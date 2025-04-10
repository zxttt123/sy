from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, BackgroundTasks, Body
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional, List
import os
import time
import tempfile
import logging
import soundfile as sf
import io
import numpy as np

from .. import database, auth
from ..models import models
from ..schemas import schemas
from ..cosyvoice_helper import CosyVoiceHelper

# 获取当前文件的日志记录器
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["synthesize"]
)

@router.post("/synthesize", response_class=FileResponse)
async def synthesize_text(
    background_tasks: BackgroundTasks,
    voice_id: str = Form(...),
    text: str = Form(...),
    user_id: Optional[int] = Depends(auth.get_current_user_id_optional),
    db: Session = Depends(database.get_db)
):
    """
    将文本合成为语音
    
    参数:
        voice_id: 声音的ID（预置声音或用户上传的声音）
        text: 要合成的文本
    
    返回:
        合成的音频文件
    """
    try:
        logger.info(f"Processing request - voice_id: {voice_id}, text length: {len(text)}")
        
        # 检查文本长度，避免空文本
        if not text or not text.strip():
            raise HTTPException(status_code=400, detail="合成文本不能为空")
        
        # 获取声音
        is_preset = False
        voice_file = None
        voice_transcript = None
        
        # 检查是否使用预置声音
        try:
            # 如果voice_id可以转换为整数，且大于0，则可能是预置声音的索引
            voice_id_int = int(voice_id)
            if voice_id_int > 0:
                cosyvoice_helper = CosyVoiceHelper()
                preset_voices = cosyvoice_helper.get_preset_voices()
                if 1 <= voice_id_int <= len(preset_voices):
                    is_preset = True
        except (ValueError, TypeError):
            # 如果不是整数，则尝试查找自定义声音
            pass
            
        # 如果不是预置声音，则查找数据库中的声音
        if not is_preset:
            voice = db.query(models.Voice).filter(models.Voice.id == voice_id).first()
            if not voice:
                raise HTTPException(status_code=404, detail=f"声音ID {voice_id} 不存在")
            
            # 检查声音是否为预置声音
            if voice.is_preset:
                is_preset = True
                voice_id = voice.name  # 使用预置声音名称
            else:
                # 检查权限 - 用户只能使用自己的声音或公开声音
                if not user_id or (voice.user_id != user_id and not voice.is_public):
                    raise HTTPException(status_code=403, detail="无权使用此声音")
                
                # 获取声音文件路径
                voice_file = os.path.join("ai_voice_server", "uploads", voice.filename)
                if not os.path.exists(voice_file):
                    raise HTTPException(status_code=404, detail="声音文件不存在")
                
                voice_transcript = voice.transcript
        
        # 创建CosyVoiceHelper实例
        cosyvoice_helper = CosyVoiceHelper()
        
        # 准备输出文件路径
        fd, output_path = tempfile.mkstemp(suffix='.wav')
        os.close(fd)
        
        # 合成语音
        if is_preset:
            # 使用预置声音合成 - 明确使用长文本兼容模式
            logger.info(f"使用预置声音合成长度为 {len(text)} 的文本")
            # 直接使用synthesize_long_text以确保支持长文本
            if len(text) > 70:  # 如果文本长，直接使用长文本处理
                cosyvoice_helper.synthesize_long_text(text, voice_id, output_path)
            else:
                cosyvoice_helper.synthesize(text, voice_id, output_path)
        else:
            # 使用自定义声音合成
            result = cosyvoice_helper.synthesize_speech(
                text=text,
                voice_id=voice_id,
                is_preset=False,
                prompt_audio=voice_file,
                prompt_text=voice_transcript
            )
            
            # 保存音频
            sf.write(output_path, result["audio_data"], result["sample_rate"])
        
        # 注册一个删除临时文件的任务
        def cleanup_temp_file(file_path: str):
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.debug(f"已删除临时文件: {file_path}")
            except Exception as e:
                logger.error(f"删除临时文件失败: {e}")
                
        background_tasks.add_task(cleanup_temp_file, output_path)
        
        # 返回音频文件
        return FileResponse(
            path=output_path,
            media_type="audio/wav",
            filename=f"synthesized_{int(time.time())}.wav"
        )
    
    except Exception as e:
        logger.exception(f"合成失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"合成失败: {str(e)}")
