from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import os
import time
import tempfile
import logging
import uuid
import json
import shutil

from ..database import get_db
from ..utils.security import oauth2_scheme, get_current_user
from ..models import models
from ..utils.audio_recognition import AudioRecognizer, convert_audio_to_wav, get_audio_duration
from ..utils.text_splitter import (
    get_audio_from_video, 
    add_subtitles_to_video, 
    replace_audio_in_video,
    create_silent_audio,
    convert_seconds_to_srt_time,
    merge_audio_files_exact
)

# 导入必要的音频处理库
import numpy as np
import soundfile as sf
try:
    import librosa
except ImportError:
    librosa = None

from ..cosyvoice_helper import CosyVoiceHelper

# 初始化日志
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/voice-replace",
    tags=["voice-replace"]
)

# 临时存储任务状态
task_status = {}

# 临时文件目录
TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传视频文件并提取音频信息"""
    if not file:
        raise HTTPException(status_code=400, detail="未上传文件")

    # 检查文件类型
    if not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
        raise HTTPException(status_code=400, detail="仅支持MP4、AVI、MOV、MKV和WEBM格式的视频")

    # 生成任务ID
    task_id = str(uuid.uuid4())
    
    # 创建任务目录
    task_dir = os.path.join(TEMP_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)
    
    try:
        # 保存上传的视频文件
        video_path = os.path.join(task_dir, file.filename)
        with open(video_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 初始化任务状态
        task_status[task_id] = {
            "status": "processing",
            "message": "正在处理视频和提取音频",
            "progress": 10,
            "created_at": time.time(),
            "user_id": current_user.id,
            "video_path": video_path,
            "original_filename": file.filename
        }
        
        return JSONResponse({
            "task_id": task_id,
            "message": "文件已上传，开始处理",
            "filename": file.filename
        })
        
    except Exception as e:
        logger.error(f"上传文件处理失败: {e}")
        # 清理任务目录
        if os.path.exists(task_dir):
            shutil.rmtree(task_dir)
        raise HTTPException(status_code=500, detail=f"上传文件处理失败: {str(e)}")

@router.get("/status/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: models.User = Depends(get_current_user)
):
    """获取任务状态"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 验证权限
    if task_status[task_id]["user_id"] != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权访问此任务")
    
    return task_status[task_id]

@router.post("/analyze/{task_id}")
async def analyze_audio(
    task_id: str,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user)
):
    """分析视频中的音频并识别语音"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 验证权限
    if task_status[task_id]["user_id"] != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权访问此任务")
    
    task_data = task_status[task_id]
    video_path = task_data["video_path"]
    
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="视频文件不存在")
    
    # 更新任务状态
    task_status[task_id]["status"] = "analyzing"
    task_status[task_id]["message"] = "正在提取音频并识别语音"
    task_status[task_id]["progress"] = 20
    
    # 在后台执行音频分析
    background_tasks.add_task(process_audio_analysis, task_id, video_path, current_user.id)
    
    return {"message": "开始分析音频", "task_id": task_id}

@router.post("/synthesize/{task_id}")
async def synthesize_audio(
    task_id: str,
    background_tasks: BackgroundTasks,
    voice_id: str = Form(...),
    is_preset: bool = Form(False),
    add_subtitles: bool = Form(True),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """使用选定的声音合成新音频并替换视频中的音频"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 验证权限
    if task_status[task_id]["user_id"] != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权访问此任务")
    
    task_data = task_status[task_id]
    
    # 验证任务状态
    if task_data.get("status") not in ["analyzed", "processing", "failed"]:
        raise HTTPException(status_code=400, detail="任务尚未完成分析或不在正确状态")
    
    # 验证任务是否有识别的文本
    if "text" not in task_data:
        raise HTTPException(status_code=400, detail="任务没有识别到文本，无法进行声音合成")
    
    # 检查视频文件是否存在
    video_path = task_data["video_path"]
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="视频文件不存在")
    
    # 验证声音ID
    try:
        # 处理预设声音
        if is_preset:
            # 验证预设声音是否存在
            cosyvoice_helper = CosyVoiceHelper(lazy_load=True)
            preset_voices = cosyvoice_helper.get_preset_voices()
            
            # 如果voice_id是数字，尝试作为索引使用
            if voice_id.isdigit():
                voice_idx = int(voice_id)
                if voice_idx < 1 or voice_idx > len(preset_voices):
                    raise HTTPException(status_code=400, detail=f"预设声音索引无效: {voice_id}")
            else:
                # 否则作为声音名称使用
                if voice_id not in preset_voices:
                    raise HTTPException(status_code=400, detail=f"预设声音名称无效: {voice_id}")
        else:
            # 验证用户声音
            voice = db.query(models.Voice).filter(models.Voice.id == voice_id).first()
            if not voice:
                raise HTTPException(status_code=404, detail=f"声音ID不存在: {voice_id}")
            
            # 检查权限
            if not voice.is_preset and voice.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="无权使用此声音")
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的声音ID格式")
    
    # 更新任务状态
    task_status[task_id]["status"] = "synthesizing"
    task_status[task_id]["message"] = "开始合成新音频"
    task_status[task_id]["progress"] = 40
    task_status[task_id]["voice_id"] = voice_id
    task_status[task_id]["is_preset"] = is_preset
    task_status[task_id]["add_subtitles"] = add_subtitles
    
    # 在后台执行音频合成
    background_tasks.add_task(process_audio_synthesis, task_id, voice_id, is_preset, add_subtitles, current_user.id, db)
    
    return {"message": "开始合成音频", "task_id": task_id}

@router.get("/download/{task_id}")
async def download_result(
    task_id: str,
    current_user: models.User = Depends(get_current_user)
):
    """下载处理结果"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 验证权限
    if task_status[task_id]["user_id"] != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权访问此任务")
    
    task_data = task_status[task_id]
    
    # 验证任务是否完成
    if task_data.get("status") != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")
    
    # 检查输出文件是否存在
    output_path = task_data.get("output_path")
    if not output_path or not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="输出文件不存在")
    
    # 获取原始文件名
    original_filename = task_data.get("original_filename", "video")
    base_name = os.path.splitext(original_filename)[0]
    output_filename = f"{base_name}_replaced.mp4"
    
    return FileResponse(
        path=output_path, 
        filename=output_filename,
        media_type="video/mp4"
    )

@router.get("/download-subtitles/{task_id}")
async def download_subtitles(
    task_id: str,
    current_user: models.User = Depends(get_current_user)
):
    """下载字幕文件"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 验证权限
    if task_status[task_id]["user_id"] != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权访问此任务")
    
    task_data = task_status[task_id]
    
    # 验证任务是否完成
    if task_data.get("status") != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")
    
    # 创建字幕文件
    task_dir = os.path.join(TEMP_DIR, task_id)
    subtitles_path = os.path.join(task_dir, "subtitles.srt")
    
    try:
        # 检查字幕文件是否已存在
        if not os.path.exists(subtitles_path) and "segments" in task_data:
            # 创建SRT格式的字幕文件
            with open(subtitles_path, 'w', encoding='utf-8') as f:
                for i, item in enumerate(task_data["segments"], 1):
                    start_time = item['start']
                    end_time = item['end']
                    text = item['text']
                    
                    # 转换为SRT格式的时间戳
                    start_str = convert_seconds_to_srt_time(start_time)
                    end_str = convert_seconds_to_srt_time(end_time)
                    
                    f.write(f"{i}\n")
                    f.write(f"{start_str} --> {end_str}\n")
                    f.write(f"{text}\n\n")
        
        # 检查字幕文件是否存在
        if not os.path.exists(subtitles_path):
            raise HTTPException(status_code=404, detail="字幕文件不存在")
        
        # 获取原始文件名
        original_filename = task_data.get("original_filename", "video")
        base_name = os.path.splitext(original_filename)[0]
        output_filename = f"{base_name}_subtitles.srt"
        
        return FileResponse(
            path=subtitles_path, 
            filename=output_filename,
            media_type="text/plain"
        )
    
    except Exception as e:
        logger.error(f"下载字幕文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载字幕文件失败: {str(e)}")

@router.post("/cleanup/{task_id}")
async def cleanup_task(
    task_id: str,
    current_user: models.User = Depends(get_current_user)
):
    """清理任务文件和状态"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 验证权限
    if task_status[task_id]["user_id"] != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="无权访问此任务")
    
    # 获取任务目录
    task_dir = os.path.join(TEMP_DIR, task_id)
    
    # 清理任务目录
    if os.path.exists(task_dir):
        try:
            shutil.rmtree(task_dir)
        except Exception as e:
            logger.error(f"清理任务目录失败: {e}")
    
    # 移除任务状态
    task_data = task_status.pop(task_id, None)
    
    return {"message": "任务已清理"}

# 后台处理函数
def process_audio_analysis(task_id: str, video_path: str, user_id: int):
    """后台处理音频分析"""
    task_dir = os.path.join(TEMP_DIR, task_id)
    audio_path = os.path.join(task_dir, "audio.wav")
    
    try:
        # 提取音频
        task_status[task_id]["message"] = "正在从视频提取音频"
        task_status[task_id]["progress"] = 25
        
        audio_path = get_audio_from_video(video_path, audio_path)
        
        # 初始化语音识别器
        task_status[task_id]["message"] = "正在加载语音识别模型"
        task_status[task_id]["progress"] = 30
        
        recognizer = AudioRecognizer(model_size="medium")
        
        # 识别语音
        task_status[task_id]["message"] = "正在识别语音内容"
        task_status[task_id]["progress"] = 40
        
        try:
            # 获取带时间戳的分段
            segments = recognizer.get_segments_with_timestamps(audio_path)
            
            # 合并所有文本
            full_text = " ".join([s["text"] for s in segments])
            
            # 将结果保存到任务状态
            task_status[task_id]["segments"] = segments
            task_status[task_id]["text"] = full_text
            task_status[task_id]["audio_path"] = audio_path
            task_status[task_id]["status"] = "analyzed"
            task_status[task_id]["message"] = "音频分析完成"
            task_status[task_id]["progress"] = 60
            
            # 保存识别结果到文件
            segments_file = os.path.join(task_dir, "segments.json")
            with open(segments_file, "w", encoding="utf-8") as f:
                json.dump(segments, f, ensure_ascii=False, indent=2)
                
            text_file = os.path.join(task_dir, "transcript.txt")
            with open(text_file, "w", encoding="utf-8") as f:
                f.write(full_text)
                
            logger.info(f"任务 {task_id} 音频分析完成，识别到 {len(segments)} 个分段")
            
        except Exception as e:
            logger.error(f"语音识别失败: {e}")
            task_status[task_id]["status"] = "failed"
            task_status[task_id]["message"] = f"语音识别失败: {str(e)}"
            task_status[task_id]["progress"] = 0
    
    except Exception as e:
        logger.error(f"音频分析过程中出错: {e}")
        task_status[task_id]["status"] = "failed"
        task_status[task_id]["message"] = f"处理失败: {str(e)}"
        task_status[task_id]["progress"] = 0

def process_audio_synthesis(task_id: str, voice_id: str, is_preset: bool, add_subtitles: bool, user_id: int, db: Session):
    """后台处理音频合成"""
    task_dir = os.path.join(TEMP_DIR, task_id)
    
    try:
        task_data = task_status[task_id]
        video_path = task_data["video_path"]
        segments_file = os.path.join(task_dir, "segments.json")
        audio_path = task_data.get("audio_path")
        
        # 确保segments.json文件存在
        if not os.path.exists(segments_file):
            raise FileNotFoundError("找不到识别结果文件segments.json")
        
        # 读取分段数据
        with open(segments_file, 'r', encoding='utf-8') as f:
            segments = json.load(f)
        
        # 初始化CosyVoice
        task_status[task_id]["message"] = "正在初始化语音合成引擎"
        task_status[task_id]["progress"] = 45
        
        cosyvoice_helper = CosyVoiceHelper()
        
        # 创建临时目录用于存储分段音频
        segments_audio_dir = os.path.join(task_dir, "segments_audio")
        os.makedirs(segments_audio_dir, exist_ok=True)
        
        # 获取原始音频的采样率信息
        sample_rate = 22050  # 默认采样率
        if os.path.exists(audio_path):
            try:
                data, rate = sf.read(audio_path)
                sample_rate = rate
            except Exception as e:
                logger.warning(f"读取原始音频采样率失败，使用默认值: {e}")
        
        # 初始化分段音频信息
        segments_audio_info = []
        processed_count = 0
        total_segments = len(segments)
        
        # 逐段处理音频合成
        task_status[task_id]["message"] = "正在分段合成音频"
        task_status[task_id]["progress"] = 50
        
        # 处理预置声音
        if is_preset:
            logger.info(f"使用预置声音 {voice_id} 合成音频")
            
            # 获取预置声音列表
            preset_voices = cosyvoice_helper.get_preset_voices()
            
            # 如果voice_id是数字或数字字符串，尝试将其映射到实际的声音名称
            if isinstance(voice_id, (int, str)) and str(voice_id).isdigit():
                voice_idx = int(voice_id)
                if 0 < voice_idx <= len(preset_voices):
                    voice_name = preset_voices[voice_idx - 1]
                    logger.info(f"将数字ID {voice_id} 映射到预置声音: {voice_name}")
                else:
                    if preset_voices:
                        voice_name = preset_voices[0]
                        logger.warning(f"无效的预置声音索引 {voice_id}，使用默认声音: {voice_name}")
                    else:
                        raise ValueError(f"无效的预置声音索引 {voice_id}，且无可用的预置声音")
            else:
                voice_name = str(voice_id)
            
            # 遍历所有分段，为每个分段合成音频
            for i, segment in enumerate(segments):
                processed_count += 1
                if processed_count % 5 == 0 or processed_count == total_segments:
                    progress = 50 + int((processed_count / total_segments) * 20)
                    task_status[task_id]["progress"] = progress
                    task_status[task_id]["message"] = f"正在合成第 {processed_count}/{total_segments} 个片段"
                
                segment_text = segment["text"].strip()
                if not segment_text:
                    continue
                
                # 为分段创建输出文件路径
                segment_audio_path = os.path.join(segments_audio_dir, f"segment_{i:04d}.wav")
                
                try:
                    # 使用cosyvoice_helper合成音频
                    result = cosyvoice_helper.synthesize(segment_text, voice_name, segment_audio_path)
                    
                    # 检查音频文件是否成功生成
                    if os.path.exists(segment_audio_path) and os.path.getsize(segment_audio_path) > 0:
                        # 获取合成的音频时长
                        audio_duration = get_audio_duration(segment_audio_path)
                        
                        # 记录分段音频信息
                        segments_audio_info.append({
                            "index": i,
                            "original_start": segment["start"],
                            "original_end": segment["end"],
                            "original_duration": segment["end"] - segment["start"],
                            "synthesized_path": segment_audio_path,
                            "synthesized_duration": audio_duration
                        })
                    else:
                        logger.warning(f"分段 {i} 的音频文件未成功生成")
                except Exception as e:
                    logger.error(f"为分段 {i} 合成音频失败: {e}")
        else:
            # 使用用户上传的声音
            logger.info(f"使用用户上传的声音 {voice_id} 合成音频")
            
            # 获取声音信息
            voice = db.query(models.Voice).filter(models.Voice.id == voice_id).first()
            if not voice:
                raise ValueError(f"声音ID不存在: {voice_id}")
            
            # 获取音频文件路径
            uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
            prompt_audio_path = os.path.join(uploads_dir, voice.filename)
            
            if not os.path.exists(prompt_audio_path):
                raise FileNotFoundError(f"提示音频文件不存在: {prompt_audio_path}")
            
            # 获取提示文本
            prompt_text = voice.transcript or "这是一段示例语音。"
            
            # 遍历所有分段，为每个分段合成音频
            for i, segment in enumerate(segments):
                processed_count += 1
                if processed_count % 5 == 0 or processed_count == total_segments:
                    progress = 50 + int((processed_count / total_segments) * 20)
                    task_status[task_id]["progress"] = progress
                    task_status[task_id]["message"] = f"正在合成第 {processed_count}/{total_segments} 个片段"
                
                segment_text = segment["text"].strip()
                if not segment_text:
                    continue
                
                # 为分段创建输出文件路径
                segment_audio_path = os.path.join(segments_audio_dir, f"segment_{i:04d}.wav")
                
                try:
                    # 使用cosyvoice_helper合成音频
                    result = cosyvoice_helper.synthesize_speech(
                        segment_text,
                        voice_id,
                        is_preset=False,
                        prompt_audio=prompt_audio_path,
                        prompt_text=prompt_text
                    )
                    
                    # 保存合成的音频
                    audio_data = result["audio_data"]
                    sample_rate = result["sample_rate"]
                    
                    # 确保音频数据类型正确
                    if audio_data.dtype != np.int16:
                        if np.issubdtype(audio_data.dtype, np.floating) and audio_data.max() <= 1.0 and audio_data.min() >= -1.0:
                            audio_data = (audio_data * 32767).astype(np.int16)
                        else:
                            audio_data = audio_data.astype(np.int16)
                    
                    # 保存到WAV文件
                    sf.write(segment_audio_path, audio_data, sample_rate)
                    
                    # 检查音频文件是否成功生成
                    if os.path.exists(segment_audio_path) and os.path.getsize(segment_audio_path) > 0:
                        # 获取合成的音频时长
                        audio_duration = get_audio_duration(segment_audio_path)
                        
                        # 记录分段音频信息
                        segments_audio_info.append({
                            "index": i,
                            "original_start": segment["start"],
                            "original_end": segment["end"],
                            "original_duration": segment["end"] - segment["start"],
                            "synthesized_path": segment_audio_path,
                            "synthesized_duration": audio_duration
                        })
                    else:
                        logger.warning(f"分段 {i} 的音频文件未成功生成")
                except Exception as e:
                    logger.error(f"为分段 {i} 合成音频失败: {e}")
        
        # 检查是否有成功合成的音频
        if not segments_audio_info:
            raise Exception("没有成功合成的音频片段")
        
        # 调整音频时长以匹配原始音频时间
        task_status[task_id]["message"] = "正在调整音频时间轴"
        task_status[task_id]["progress"] = 70
        
        # 创建最终合成的音频文件路径
        final_audio_path = os.path.join(task_dir, "synthesized_audio.wav")
        
        # 计算所有音频段的总持续时间
        total_original_duration = sum(info["original_duration"] for info in segments_audio_info)
        total_synthesized_duration = sum(info["synthesized_duration"] for info in segments_audio_info)
        
        logger.info(f"原始音频总时长: {total_original_duration:.2f}秒")
        logger.info(f"合成音频总时长: {total_synthesized_duration:.2f}秒")
        
        # 根据原始时长调整音频
        adjusted_segments = []
        current_position = 0
        
        # 创建一个列表存储所有音频片段及其时间位置
        aligned_segments = []
        
        for info in segments_audio_info:
            original_start = info["original_start"]
            original_duration = info["original_duration"]
            synthesized_path = info["synthesized_path"]
            
            # 如果当前位置小于原始开始时间，添加一段静音
            if current_position < original_start:
                silence_duration = original_start - current_position
                silence_path = os.path.join(segments_audio_dir, f"silence_{len(aligned_segments):04d}.wav")
                
                # 创建静音文件
                silent_data = create_silent_audio(silence_duration, sample_rate, silence_path)
                
                aligned_segments.append({
                    "path": silence_path,
                    "start": current_position,
                    "duration": silence_duration,
                    "end": original_start
                })
                
                current_position = original_start
            
            # 添加合成的音频段
            try:
                # 读取音频数据和采样率
                audio_data, audio_sample_rate = sf.read(synthesized_path)
                 
                # 检查音频长度是否需要调整
                audio_duration = len(audio_data) / audio_sample_rate
                
                # 根据原始时长调整音频
                if abs(audio_duration - original_duration) > 0.1:  # 如果差异超过0.1秒
                    # 检查是否可用librosa，否则跳过调整
                    if librosa is None:
                        logger.warning("librosa模块不可用，跳过音频时长调整")
                        aligned_segments.append({
                            "path": synthesized_path,
                            "start": original_start,
                            "duration": original_duration,
                            "end": original_start + original_duration
                        })
                    else:
                        # 将音频缩放到原始时长
                        try:
                            # 调整音频速度但保持音高
                            y, sr = librosa.load(synthesized_path, sr=audio_sample_rate)
                            y_adjusted = librosa.effects.time_stretch(y, rate=audio_duration/original_duration)
                            
                            # 保存调整后的音频
                            adjusted_path = os.path.join(segments_audio_dir, f"adjusted_{len(aligned_segments):04d}.wav")
                            sf.write(adjusted_path, y_adjusted, sr)
                            
                            aligned_segments.append({
                                "path": adjusted_path,
                                "start": original_start,
                                "duration": original_duration,
                                "end": original_start + original_duration
                            })
                        except Exception as e:
                            logger.error(f"调整音频时长失败: {e}")
                            # 使用原始音频
                            aligned_segments.append({
                                "path": synthesized_path,
                                "start": original_start,
                                "duration": original_duration,
                                "end": original_start + original_duration
                            })
                else:
                    # 不需要调整
                    aligned_segments.append({
                        "path": synthesized_path,
                        "start": original_start,
                        "duration": original_duration,
                        "end": original_start + original_duration
                    })
                
                current_position = original_start + original_duration
                
            except Exception as e:
                logger.error(f"处理音频段失败: {e}")
                # 如果处理失败，使用静音代替
                silence_path = os.path.join(segments_audio_dir, f"error_silence_{len(aligned_segments):04d}.wav")
                silent_data = create_silent_audio(original_duration, sample_rate, silence_path)
                
                aligned_segments.append({
                    "path": silence_path,
                    "start": original_start,
                    "duration": original_duration,
                    "end": original_start + original_duration
                })
                
                current_position = original_start + original_duration
        
        # 合并所有音频段
        task_status[task_id]["message"] = "正在合并音频片段"
        task_status[task_id]["progress"] = 80
        
        # 准备要合并的音频文件列表
        audio_files = [segment["path"] for segment in aligned_segments]
        
        # 直接合并音频文件，无需再导入merge_audio_files_exact
        merge_result = merge_audio_files_exact(audio_files, final_audio_path, crossfade_duration=0.05)
        
        if not os.path.exists(final_audio_path) or os.path.getsize(final_audio_path) == 0:
            raise Exception("合并音频失败，输出文件不存在或为空")
        
        # 替换视频中的音频
        task_status[task_id]["message"] = "正在替换视频音频"
        task_status[task_id]["progress"] = 85
        
        # 替换音频
        output_video_path = os.path.join(task_dir, "output_video_no_subtitles.mp4")
        replaced_video = replace_audio_in_video(video_path, final_audio_path, output_video_path)
        
        # 如果需要添加字幕
        if add_subtitles:
            task_status[task_id]["message"] = "正在添加字幕"
            task_status[task_id]["progress"] = 90
            
            # 创建最终输出文件路径
            final_output_path = os.path.join(task_dir, "output_video_with_subtitles.mp4")
            
            # 添加字幕
            final_video = add_subtitles_to_video(replaced_video, segments, final_output_path)
            output_path = final_video
        else:
            output_path = replaced_video
        
        # 保存字幕文件，即使不需要添加到视频中也保存，以便于单独下载
        subtitles_file = os.path.join(task_dir, "subtitles.srt")
        with open(subtitles_file, "w", encoding="utf-8") as f:
            for i, item in enumerate(segments, 1):
                start_time = item['start']
                end_time = item['end']
                text = item['text']
                
                # 转换为SRT格式的时间戳
                start_str = convert_seconds_to_srt_time(start_time)
                end_str = convert_seconds_to_srt_time(end_time)
                
                f.write(f"{i}\n")
                f.write(f"{start_str} --> {end_str}\n")
                f.write(f"{text}\n\n")
        
        # 更新任务状态
        task_status[task_id]["status"] = "completed"
        task_status[task_id]["message"] = "处理完成"
        task_status[task_id]["progress"] = 100
        task_status[task_id]["output_path"] = output_path
        
        logger.info(f"任务 {task_id} 处理完成，输出文件: {output_path}")
        
        # 记录语音合成日志
        try:
            synthesis_log = models.SynthesisLog(
                type="voice_replace",
                user_id=user_id,
                voice_id=None if is_preset else int(voice_id),
                text_length=sum(len(segment["text"]) for segment in segments),
                duration=total_original_duration
            )
            db.add(synthesis_log)
            db.commit()
        except Exception as e:
            logger.error(f"记录合成日志失败: {e}")
    
    except Exception as e:
        logger.error(f"音频合成过程中出错: {e}")
        task_status[task_id]["status"] = "failed"
        task_status[task_id]["message"] = f"处理失败: {str(e)}"
        task_status[task_id]["progress"] = 0

def convert_seconds_to_srt_time(seconds: float) -> str:
    """将秒数转换为SRT格式的时间戳"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{int(seconds):02},{milliseconds:03}"
