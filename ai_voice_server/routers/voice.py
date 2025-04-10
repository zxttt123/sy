from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import os
import io
import wave
import numpy as np
import scipy.io.wavfile as wav  # 添加scipy波形文件支持
import time
import sys
from typing import Optional
from ..database import get_db
from ..models import models
from ..utils.security import oauth2_scheme, get_current_user

# 设置路径
COSYVOICE_PATH = os.path.expanduser('~/CosyVoice')
MATCHA_TTS_PATH = os.path.join(COSYVOICE_PATH, 'third_party/Matcha-TTS')
sys.path.extend([COSYVOICE_PATH, MATCHA_TTS_PATH])

# 从cosyvoice_helper导入单例，不再直接初始化模型
from cosyvoice.utils.file_utils import load_wav

router = APIRouter()

# 设置上传目录
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
print(f"Upload directory set to: {UPLOAD_DIR}")

# 移除在此处初始化CosyVoice模型的代码

@router.get("/voices")
async def get_voices(
    type: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        if type == "preset":
            # 获取预置声音，这些应该归属于 system 用户
            voices = db.query(models.Voice).filter(models.Voice.is_preset == True).all()
            return voices
        else:
            # 只获取当前用户上传的声音，不是预置声音
            voices = db.query(models.Voice).filter(
                models.Voice.user_id == current_user.id,  
                models.Voice.is_preset == False
            ).all()
            return voices
    except Exception as e:
        print(f"获取声音列表错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取声音列表失败: {str(e)}"
        )

@router.post("/upload")
async def upload_voice(
    audio: UploadFile = File(...),
    prompt_text: str = Form(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file_path = None
    try:
        print(f"Uploading file: {audio.filename}, content_type: {audio.content_type}")
        
        if not audio.filename.lower().endswith(('.wav', '.mp3')):
            raise HTTPException(
                status_code=400,
                detail="Only .wav and .mp3 files are allowed"
            )

        # 确保上传目录存在
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        # 检查目录权限
        try:
            test_file_path = os.path.join(UPLOAD_DIR, "test_write_permission.tmp")
            with open(test_file_path, 'w') as test_file:
                test_file.write("test")
            os.remove(test_file_path)
            print("Upload directory has write permission")
        except Exception as e:
            print(f"Permission test failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Server upload directory permission error: {str(e)}"
            )

        # 创建唯一文件名
        file_extension = os.path.splitext(audio.filename)[1]
        unique_filename = f"{current_user.id}_{int(time.time())}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        print(f"Saving file to: {file_path}")
        
        # 读取文件内容并写入
        try:
            content = await audio.read()
            print(f"Read {len(content)} bytes from upload")
            
            with open(file_path, 'wb') as out_file:
                out_file.write(content)
            
            # 验证文件是否成功写入
            if not os.path.exists(file_path):
                raise Exception(f"File does not exist after write: {file_path}")
                
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                raise Exception("File was created but is empty")
                
            print(f"File saved successfully: {file_path}, size: {file_size} bytes")
        except Exception as e:
            print(f"File write error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error writing file: {str(e)}"
            )

        # 保存到数据库 - 修改此处，使用正确的字段名：filename 而非 file_path
        try:
            db_voice = models.Voice(
                name=audio.filename,
                filename=unique_filename,  # 使用 filename 而非 file_path
                transcript=prompt_text,    # 使用 transcript 而非 prompt_text
                user_id=current_user.id    # 使用 user_id 而非 owner_id
            )
            db.add(db_voice)
            db.commit()
            db.refresh(db_voice)
            print(f"Voice record added to database with ID: {db_voice.id}")
        except Exception as e:
            print(f"Database error: {str(e)}")
            # 如果数据库操作失败，删除上传的文件
            if os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(
                status_code=500,
                detail=f"Database error: {str(e)}"
            )
        
        return {"message": "Voice uploaded successfully", "voice_id": db_voice.id}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unhandled error in upload_voice: {str(e)}")
        # 清理临时文件
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Cleaned up file after error: {file_path}")
            except Exception as cleanup_error:
                print(f"Failed to clean up file: {cleanup_error}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )

@router.post("/synthesize")
async def synthesize_voice(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    try:
        form = await request.form()
        
        # 获取并验证voice_id
        voice_id = form.get("voice_id")
        if not voice_id:
            raise HTTPException(
                status_code=400,
                detail="voice_id is required"
            )
            
        try:
            voice_id = int(voice_id)
        except ValueError:
            # 尝试处理预置声音名称作为ID
            preset_voices = db.query(models.Voice).filter(
                models.Voice.name == voice_id,
                models.Voice.is_preset == True
            ).all()
            
            if preset_voices:
                voice_id = preset_voices[0].id
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid voice_id format"
                )
        
        target_text = form.get("target_text", "").strip()
        if not target_text:
            raise HTTPException(
                status_code=400,
                detail="target_text is required"
            )

        print(f"Processing request - voice_id: {voice_id}, text length: {len(target_text)}")

        # 获取声音
        voice = db.query(models.Voice).filter(models.Voice.id == voice_id).first()
        if not voice:
            raise HTTPException(
                status_code=404,
                detail=f"Voice not found with id {voice_id}"
            )

        # 检查是否为预置声音
        if voice.is_preset:
            # 使用CosyVoice模型的单例实例进行合成
            from ai_voice_server.cosyvoice_helper import CosyVoiceHelper
            cosyvoice_helper = CosyVoiceHelper()
            result = cosyvoice_helper.synthesize_speech(target_text, voice.name, is_preset=True)
            
            # 确保音频数据是整数类型，防止因为float类型导致无声音
            audio_data = result["audio_data"]
            if audio_data.dtype != np.int16:
                # 将浮点数据归一化到 [-32768, 32767] 范围然后转换为int16
                if audio_data.max() <= 1.0 and audio_data.min() >= -1.0:
                    audio_data = (audio_data * 32767).astype(np.int16)
                else:
                    audio_data = audio_data.astype(np.int16)
            
            # 创建WAV文件在内存中
            buffer = io.BytesIO()
            wav.write(buffer, result["sample_rate"], audio_data)
            
            buffer.seek(0)
            audio_duration = len(audio_data) / result["sample_rate"]

            # 记录语音合成日志
            synthesis_log = models.SynthesisLog(
                type="voice",
                user_id=current_user.id,
                voice_id=None,
                text_length=len(target_text),
                duration=audio_duration
            )
            db.add(synthesis_log)
            db.commit()

            return StreamingResponse(
                buffer,
                media_type="audio/wav",
                headers={
                    "Content-Disposition": f'attachment; filename="synthesized_{voice_id}.wav"'
                }
            )
        
        # 非预置声音，使用上传的音频文件
        # 构建完整的音频文件路径
        uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
        audio_path = os.path.join(uploads_dir, voice.filename)
        
        # 检查文件是否存在
        if not os.path.exists(audio_path):
            raise HTTPException(
                status_code=404, 
                detail=f"Voice file not found: {voice.filename}"
            )
        
        # 使用CosyVoiceHelper而不是直接使用全局变量
        from ai_voice_server.cosyvoice_helper import CosyVoiceHelper
        cosyvoice_helper = CosyVoiceHelper()
        
        # 加载音频
        prompt_speech_16k = load_wav(audio_path, 16000)
        
        # 分段合成处理长文本
        sentences = target_text.split('。')
        sentences = [s + '。' for s in sentences if s.strip()]
        
        all_audio_data = []
        sample_rate = 22050
        
        # 添加短暂的静音作为句子间隔
        silence_duration = 0.2
        silence_samples = int(silence_duration * sample_rate)
        silence = np.zeros(silence_samples, dtype=np.int16)
        
        for i, sentence in enumerate(sentences):
            if not sentence.strip():
                continue
                
            print(f"Synthesizing sentence {i+1}/{len(sentences)}: {sentence}")
            
            try:
                result = cosyvoice_helper.synthesize_speech(
                    sentence, 
                    voice_id, 
                    is_preset=False,
                    prompt_audio=audio_path,
                    prompt_text=voice.transcript
                )

                # 获取音频数据并确保是int16类型
                audio_array = result["audio_data"]
                
                # 检查音频数据的类型和范围
                print(f"Audio data type: {audio_array.dtype}, shape: {audio_array.shape}")
                print(f"Audio range: min={audio_array.min()}, max={audio_array.max()}")
                
                # 确保是整数类型，防止因为float类型导致无声音
                if audio_array.dtype != np.int16:
                    # 将浮点数据归一化到 [-32768, 32767] 范围然后转换为int16
                    if audio_array.max() <= 1.0 and audio_array.min() >= -1.0:
                        audio_array = (audio_array * 32767).astype(np.int16)
                    else:
                        audio_array = audio_array.astype(np.int16)
                
                if len(audio_array.shape) > 1:
                    audio_array = audio_array.flatten()
                all_audio_data.append(audio_array)
                
                if i < len(sentences) - 1:  # 不在最后一句后添加静音
                    all_audio_data.append(silence)

            except Exception as e:
                print(f"Error synthesizing sentence {i+1}: {str(e)}")
                continue

        if not all_audio_data:
            raise HTTPException(
                status_code=500,
                detail="No audio generated"
            )

        print("Concatenating audio segments...")
        combined_audio = np.concatenate(all_audio_data)
        print(f"Combined audio shape: {combined_audio.shape}")
        print(f"Combined audio type: {combined_audio.dtype}")
        print(f"Combined audio range: min={combined_audio.min()}, max={combined_audio.max()}")
        
        # 创建WAV文件在内存中
        buffer = io.BytesIO()
        wav.write(buffer, sample_rate, combined_audio)
        
        buffer.seek(0)
        audio_duration = len(combined_audio) / sample_rate

        # 记录语音合成日志
        synthesis_log = models.SynthesisLog(
            type="voice",
            user_id=current_user.id,
            voice_id=voice_id,
            text_length=len(target_text),
            duration=audio_duration
        )
        db.add(synthesis_log)
        db.commit()

        return StreamingResponse(
            buffer,
            media_type="audio/wav",
            headers={
                "Content-Disposition": f'attachment; filename="synthesized_{voice_id}.wav"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Synthesis error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to synthesize speech: {str(e)}"
        )