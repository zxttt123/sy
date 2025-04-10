"""
文本分段处理工具，用于长文本语音合成
"""

import re
import logging
import tempfile
import os
import numpy as np
import soundfile as sf
from scipy import signal
from typing import List, Dict, Any, Optional
import subprocess
import json

logger = logging.getLogger(__name__)

# 中文文本分割标点符号 - 增加更多标点以获得更好的分段效果
CHINESE_SENT_SEP = r'[，。！？；：、\n,.!?;:\r"]'
# 最大文本长度（字符数，根据测试调整）
MAX_TEXT_LENGTH = 70

def split_text(text: str) -> List[str]:
    """
    将文本按标点符号分割成句子
    
    参数:
        text: 输入文本
        
    返回:
        句子列表
    """
    if not text:
        return []
    
    # 记录原始文本信息
    logger.debug(f"分割文本，原始长度: {len(text)}")
        
    # 按标点符号切分文本
    pattern = r'([。！？?!,，;；\n])'
    sentences = []
    
    # 先按段落分割
    paragraphs = text.split('\n')
    
    for paragraph in paragraphs:
        if not paragraph.strip():
            continue
            
        # 按标点符号分割段落
        parts = re.split(pattern, paragraph)
        
        current_sentence = ""
        for i in range(0, len(parts)):
            current_sentence += parts[i]
            
            # 如果是标点符号则将句子添加到结果中
            if i % 2 == 1:
                if current_sentence.strip():
                    sentences.append(current_sentence.strip())
                current_sentence = ""
        
        # 处理不以标点符号结尾的剩余文本
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
    
    # 记录分割结果
    logger.debug(f"文本分割完成，共 {len(sentences)} 个句子")
    # 显示前几个句子的内容用于调试
    for i, sent in enumerate(sentences[:5]):
        logger.debug(f"句子 {i+1}: '{sent}'")
    
    return sentences

def merge_sentences_into_chunks(sentences: List[str], max_chunk_length: int) -> List[str]:
    """
    将句子合并为合适长度的文本块
    
    参数:
        sentences: 句子列表
        max_chunk_length: 每个块的最大字符数
        
    返回:
        文本块列表
    """
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        # 如果单个句子长度超过最大长度，则单独作为一个块
        if len(sentence) > max_chunk_length:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            chunks.append(sentence)
            continue
        
        # 判断添加当前句子后是否超过最大长度
        if len(current_chunk) + len(sentence) > max_chunk_length:
            chunks.append(current_chunk)
            current_chunk = sentence
        else:
            if current_chunk:
                current_chunk += " "
            current_chunk += sentence
    
    # 添加最后一个块
    if current_chunk:
        chunks.append(current_chunk)
    
    # 记录合并结果
    logger.debug(f"合并为 {len(chunks)} 个文本块")
    for i, chunk in enumerate(chunks[:5]):
        logger.debug(f"块 {i+1}: '{chunk}', 长度: {len(chunk)}")
    
    return chunks

def merge_audio_files(audio_files: List[str], output_path: str, crossfade_duration: float = 0.1) -> str:
    """
    合并多个音频文件，并添加交叉淡入淡出效果
    
    参数:
        audio_files: 音频文件路径列表
        output_path: 输出文件路径
        crossfade_duration: 交叉淡入淡出时长(秒)
        
    返回:
        输出文件路径
    """
    if not audio_files:
        logger.error("没有音频文件需要合并")
        return None
        
    if len(audio_files) == 1:
        # 如果只有一个文件，直接返回它
        if output_path:
            import shutil
            shutil.copy(audio_files[0], output_path)
            return output_path
        return audio_files[0]
    
    # 读取所有音频文件
    audio_segments = []
    sample_rate = None
    
    for audio_file in audio_files:
        data, rate = sf.read(audio_file)
        
        # 确保采样率一致
        if sample_rate is None:
            sample_rate = rate
        elif rate != sample_rate:
            # 简单处理：转换为相同采样率
            # 在实际项目中可以使用librosa.resample等进行更复杂的处理
            raise ValueError(f"采样率不匹配: {rate} != {sample_rate}")
        
        audio_segments.append(data)
    
    # 如果只有一个音频文件，直接返回
    if len(audio_segments) == 1:
        sf.write(output_path, audio_segments[0], sample_rate)
        return output_path
    
    # 计算交叉淡入淡出样本数
    crossfade_samples = int(crossfade_duration * sample_rate)
    
    # 合并音频段
    result = audio_segments[0]
    
    for i in range(1, len(audio_segments)):
        # 当前段
        current_audio = audio_segments[i]
        
        # 计算合并点
        merge_point = len(result) - crossfade_samples
        
        # 创建渐变权重
        fade_out = np.linspace(1, 0, crossfade_samples)
        fade_in = np.linspace(0, 1, crossfade_samples)
        
        # 确保数据形状兼容（处理单声道/多声道）
        if len(result.shape) > 1 and len(current_audio.shape) > 1:
            # 多声道情况
            for channel in range(result.shape[1]):
                result[merge_point:merge_point+crossfade_samples, channel] *= fade_out
                current_audio[:crossfade_samples, channel] *= fade_in
        else:
            # 单声道情况
            result[merge_point:merge_point+crossfade_samples] *= fade_out
            current_audio[:crossfade_samples] *= fade_in
        
        # 合并音频
        merged = np.concatenate([result[:merge_point], 
                                result[merge_point:merge_point+crossfade_samples] + current_audio[:crossfade_samples], 
                                current_audio[crossfade_samples:]])
        result = merged
    
    # 保存结果
    sf.write(output_path, result, sample_rate)
    logger.info(f"已合并 {len(audio_files)} 个音频片段到 {output_path}")
    return output_path

def get_audio_duration(audio_file: str) -> float:
    """
    获取音频文件的播放时长（秒）
    
    参数:
        audio_file: 音频文件路径
        
    返回:
        音频时长（秒）
    """
    try:
        data, sample_rate = sf.read(audio_file)
        duration = len(data) / sample_rate
        logger.debug(f"音频文件 {os.path.basename(audio_file)} 时长: {duration:.2f}秒")
        return duration
    except Exception as e:
        logger.error(f"获取音频时长失败: {str(e)}")
        return 0.0

def merge_audio_files_exact(audio_files: List[str], output_path: str, crossfade_duration: float = 0.05) -> Dict[str, Any]:
    """
    合并多个音频文件，添加精确的交叉淡入淡出效果，并返回时间信息
    
    参数:
        audio_files: 音频文件路径列表
        output_path: 输出文件路径
        crossfade_duration: 交叉淡入淡出时长(秒)
        
    返回:
        包含时间信息的字典：{
            'path': 输出文件路径,
            'duration': 总时长,
            'segments': [{
                'file': 文件路径,
                'start': 在合并音频中的开始时间(秒),
                'duration': 原始持续时间(秒),
                'end': 在合并音频中的结束时间(秒)
            }]
        }
    """
    if not audio_files:
        logger.error("没有音频文件需要合并")
        return {'path': None, 'duration': 0, 'segments': []}
        
    if len(audio_files) == 1:
        # 如果只有一个文件，直接返回它
        duration = get_audio_duration(audio_files[0])
        if output_path:
            import shutil
            shutil.copy(audio_files[0], output_path)
            return {
                'path': output_path, 
                'duration': duration,
                'segments': [{'file': audio_files[0], 'start': 0, 'duration': duration, 'end': duration}]
            }
        return {
            'path': audio_files[0], 
            'duration': duration,
            'segments': [{'file': audio_files[0], 'start': 0, 'duration': duration, 'end': duration}]
        }
    
    # 读取所有音频文件
    audio_segments = []
    sample_rate = None
    segment_info = []
    current_position = 0  # 当前位置(秒)
    
    for audio_file in audio_files:
        data, rate = sf.read(audio_file)
        
        # 确保采样率一致
        if sample_rate is None:
            sample_rate = rate
        elif rate != sample_rate:
            # 简单处理：转换为相同采样率
            # 在实际项目中可以使用librosa.resample等进行更复杂的处理
            raise ValueError(f"采样率不匹配: {rate} != {sample_rate}")
        
        # 记录原始持续时间
        orig_duration = len(data) / sample_rate
        
        # 存储数据和对应信息
        audio_segments.append(data)
        segment_info.append({
            'file': audio_file,
            'start': current_position,
            'duration': orig_duration,
            'end': current_position + orig_duration
        })
        
        # 更新当前位置，考虑到交叉淡入淡出的重叠
        if len(audio_segments) > 1:  # 第二个及后续片段考虑交叉淡入淡出
            current_position += orig_duration - crossfade_duration
        else:  # 第一个片段完整计算
            current_position += orig_duration
    
    # 如果只有一个音频文件，直接返回
    if len(audio_segments) == 1:
        sf.write(output_path, audio_segments[0], sample_rate)
        return {
            'path': output_path, 
            'duration': segment_info[0]['duration'],
            'segments': segment_info
        }
    
    # 计算交叉淡入淡出样本数
    crossfade_samples = int(crossfade_duration * sample_rate)
    
    # 合并音频段，同时更新时间信息
    result = audio_segments[0]
    
    for i in range(1, len(audio_segments)):
        # 当前段
        current_audio = audio_segments[i]
        
        # 计算合并点
        merge_point = len(result) - crossfade_samples
        
        # 创建渐变权重
        fade_out = np.linspace(1, 0, crossfade_samples)
        fade_in = np.linspace(0, 1, crossfade_samples)
        
        # 确保数据形状兼容（处理单声道/多声道）
        if len(result.shape) > 1 and len(current_audio.shape) > 1:
            # 多声道情况
            for channel in range(result.shape[1]):
                result[merge_point:merge_point+crossfade_samples, channel] *= fade_out
                current_audio[:crossfade_samples, channel] *= fade_in
        else:
            # 单声道情况
            result[merge_point:merge_point+crossfade_samples] *= fade_out
            current_audio[:crossfade_samples] *= fade_in
        
        # 合并音频
        merged = np.concatenate([result[:merge_point], 
                                result[merge_point:merge_point+crossfade_samples] + current_audio[:crossfade_samples], 
                                current_audio[crossfade_samples:]])
        result = merged
        
        # 更新后续片段的时间信息（因为交叉淡入淡出导致实际开始时间提前）
        for j in range(i+1, len(segment_info)):
            # 每个后续片段的开始和结束时间都要考虑当前的交叉淡入淡出时间
            segment_info[j]['start'] -= crossfade_duration
            segment_info[j]['end'] -= crossfade_duration
    
    # 计算实际的总时长
    total_duration = len(result) / sample_rate
    
    # 保存结果
    sf.write(output_path, result, sample_rate)
    logger.info(f"已合并 {len(audio_files)} 个音频片段到 {output_path}，总时长: {total_duration:.2f}秒")
    
    return {
        'path': output_path,
        'duration': total_duration,
        'segments': segment_info
    }

def get_audio_from_video(video_path: str, output_audio_path: Optional[str] = None) -> str:
    """
    从视频文件中提取音频
    
    参数:
        video_path: 视频文件路径
        output_audio_path: 输出音频文件路径，如果为None则自动生成
    
    返回:
        输出的音频文件路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")
    
    if not output_audio_path:
        # 创建临时文件作为输出
        fd, output_audio_path = tempfile.mkstemp(suffix='.wav')
        os.close(fd)
    
    try:
        # 使用ffmpeg提取音频
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vn",  # 不处理视频
            "-acodec", "pcm_s16le",  # 输出为16位PCM
            "-ar", "16000",  # 采样率设为16kHz
            "-ac", "1",  # 单声道
            "-y",  # 覆盖已有文件
            output_audio_path
        ]
        
        logger.info(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True)
        
        if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 0:
            logger.info(f"成功从视频提取音频: {output_audio_path}")
            return output_audio_path
        else:
            raise RuntimeError("提取音频失败，输出文件不存在或为空")
            
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8', errors='replace') if e.stderr else str(e)
        logger.error(f"提取音频失败: {error_msg}")
        raise RuntimeError(f"提取音频失败: {error_msg}")
    except Exception as e:
        logger.error(f"提取音频过程中发生错误: {str(e)}")
        raise

def add_subtitles_to_video(video_path: str, subtitles_data: List[Dict[str, Any]], 
                           output_path: Optional[str] = None, font_size: int = 24, 
                           font_color: str = "white", border_color: str = "black",
                           position: str = "bottom") -> str:
    """
    为视频添加字幕
    
    参数:
        video_path: 视频文件路径
        subtitles_data: 字幕数据，格式为[{"start": 开始时间(秒), "end": 结束时间(秒), "text": "字幕文本"}, ...]
        output_path: 输出视频路径，如果为None则自动生成
        font_size: 字体大小
        font_color: 字体颜色
        border_color: 边框颜色
        position: 字幕位置，可选 "bottom" 或 "top"
        
    返回:
        输出视频的路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")
        
    if not subtitles_data:
        raise ValueError("字幕数据不能为空")
    
    if not output_path:
        # 创建临时文件用于输出
        fd, output_path = tempfile.mkstemp(suffix='.mp4')
        os.close(fd)
    
    try:
        # 首先创建SRT格式的字幕文件
        fd, srt_path = tempfile.mkstemp(suffix='.srt')
        os.close(fd)
        
        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, item in enumerate(subtitles_data, 1):
                start_time = item['start']
                end_time = item['end']
                text = item['text']
                
                # 转换为SRT格式的时间戳 HH:MM:SS,mmm
                start_str = convert_seconds_to_srt_time(start_time)
                end_str = convert_seconds_to_srt_time(end_time)
                
                f.write(f"{i}\n")
                f.write(f"{start_str} --> {end_str}\n")
                f.write(f"{text}\n\n")
        
        # 设置字幕位置
        y_position = "h-th-60" if position == "bottom" else "10"
        
        # 使用ffmpeg添加字幕
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vf", f"subtitles={srt_path}:force_style='FontName=Arial,FontSize={font_size},PrimaryColour=&H{get_color_code(font_color)},OutlineColour=&H{get_color_code(border_color)},BorderStyle=1,Outline=1,Alignment=2,MarginV={y_position}'",
            "-c:a", "copy",  # 复制音频流
            "-y",  # 覆盖已有文件
            output_path
        ]
        
        logger.info(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True)
        
        # 清理临时字幕文件
        if os.path.exists(srt_path):
            os.remove(srt_path)
            
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"成功为视频添加字幕: {output_path}")
            return output_path
        else:
            raise RuntimeError("添加字幕失败，输出文件不存在或为空")
            
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8', errors='replace') if e.stderr else str(e)
        logger.error(f"添加字幕失败: {error_msg}")
        raise RuntimeError(f"添加字幕失败: {error_msg}")
    except Exception as e:
        logger.error(f"添加字幕过程中发生错误: {str(e)}")
        raise

def convert_seconds_to_srt_time(seconds: float) -> str:
    """将秒数转换为SRT格式的时间戳 HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    msec = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{msec:03d}"

def get_color_code(color_name: str) -> str:
    """将颜色名称转换为16进制颜色代码"""
    color_map = {
        "white": "FFFFFF",
        "black": "000000",
        "red": "FF0000",
        "green": "00FF00",
        "blue": "0000FF",
        "yellow": "FFFF00",
        "cyan": "00FFFF",
        "magenta": "FF00FF",
    }
    return color_map.get(color_name.lower(), "FFFFFF")  # 默认为白色

def create_silent_audio(duration: float, sample_rate: int = 22050, output_path: str = None) -> np.ndarray:
    """
    创建指定时长的静音音频
    
    参数:
        duration: 音频时长(秒)
        sample_rate: 采样率
        output_path: 输出文件路径，如果为None则不保存文件
        
    返回:
        numpy数组形式的音频数据
    """
    # 计算采样点数
    num_samples = int(duration * sample_rate)
    
    # 创建静音数据
    silent_data = np.zeros(num_samples, dtype=np.int16)
    
    # 如果需要保存到文件
    if output_path:
        sf.write(output_path, silent_data, sample_rate)
    
    return silent_data

def replace_audio_in_video(video_path: str, audio_path: str, output_path: Optional[str] = None) -> str:
    """
    替换视频中的音频
    
    参数:
        video_path: 视频文件路径
        audio_path: 新的音频文件路径
        output_path: 输出视频路径，如果为None则自动生成
        
    返回:
        输出视频的路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")
    
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")
    
    if not output_path:
        # 创建临时文件用于输出
        fd, output_path = tempfile.mkstemp(suffix='.mp4')
        os.close(fd)
    
    try:
        # 使用ffmpeg替换音频
        cmd = [
            "ffmpeg",
            "-i", video_path,  # 输入视频
            "-i", audio_path,  # 输入音频
            "-map", "0:v",     # 使用第一个输入的视频流
            "-map", "1:a",     # 使用第二个输入的音频流
            "-c:v", "copy",    # 复制视频编码
            "-shortest",       # 以最短的流长度为准
            "-y",              # 覆盖已有文件
            output_path
        ]
        
        logger.info(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"成功替换视频音频: {output_path}")
            return output_path
        else:
            raise RuntimeError("替换音频失败，输出文件不存在或为空")
            
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8', errors='replace') if e.stderr else str(e)
        logger.error(f"替换音频失败: {error_msg}")
        raise RuntimeError(f"替换音频失败: {error_msg}")
    except Exception as e:
        logger.error(f"替换音频过程中发生错误: {str(e)}")
        raise

if __name__ == "__main__":
    # 简单测试
    text = "这是一个测试句子。这是第二个句子！这是最后一个句子？"
    sentences = split_text(text)
    print(sentences)
    
    chunks = merge_sentences_into_chunks(sentences, 10)
    print(chunks)
