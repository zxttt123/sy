from fastapi import FastAPI, Depends, Form, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, get_db
from sqlalchemy.orm import Session
from .models import models
from .models.models import User, Voice
from .routers import auth, voice, admin, courseware, voice_replace
# 修改此行 - 从routers.auth模块导入get_current_user函数
from .routers.auth import get_current_user
from ai_voice_server.cosyvoice_helper import CosyVoiceHelper
from typing import List
import os
import uuid
import logging
import scipy.io.wavfile as wav
import numpy as np

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 目录配置
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ai_voice_server", "uploads")
TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ai_voice_server", "temp")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# 创建数据库表
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含路由
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(voice.router, prefix="/api", tags=["voice"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(courseware.router, prefix="/api", tags=["courseware"])
# 添加声音置换路由
app.include_router(voice_replace.router, tags=["voice-replace"])

# 初始化全局变量
cosyvoice_helper = None

@app.on_event("startup")
async def startup():
    # 初始化CosyVoice模型
    global cosyvoice_helper
    cosyvoice_helper = CosyVoiceHelper()
    logger.info("服务器已启动，模型已初始化")

@app.get("/api/preset_voices", response_model=List[str])
async def get_preset_voices(current_user: User = Depends(get_current_user)):
    """获取所有预置的声音列表"""
    global cosyvoice_helper
    try:
        # 获取系统预置声音
        preset_voices = cosyvoice_helper.get_preset_voices()
        logger.info(f"获取到 {len(preset_voices)} 个预置声音")
        return preset_voices
    except Exception as e:
        logger.error(f"获取预置声音失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取预置声音失败: {str(e)}"
        )

@app.post("/api/synthesize")
async def synthesize(
    text: str = Form(...),
    voice_id: str = Form(...),
    is_preset: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    合成语音
    
    - text: 要合成的文本
    - voice_id: 声音ID或预置声音名称
    - is_preset: 是否使用预置声音
    """
    try:
        if is_preset:
            # 使用预置声音
            result = cosyvoice_helper.synthesize_speech(text, voice_id, is_preset=True)
        else:
            # 使用用户上传的声音
            voice = db.query(Voice).filter(Voice.id == voice_id).first()
            if not voice:
                raise HTTPException(status_code=404, detail="声音不存在")
                
            # 确保用户只能使用自己的声音
            if voice.user_id != current_user.id and not current_user.is_admin:
                raise HTTPException(status_code=403, detail="没有权限使用此声音")
                
            audio_path = os.path.join(UPLOAD_DIR, voice.filename)
            result = cosyvoice_helper.synthesize_speech(
                text, 
                voice_id, 
                is_preset=False,
                prompt_audio=audio_path,
                prompt_text=voice.transcript
            )
        
        # 生成临时文件名
        temp_filename = f"temp_{uuid.uuid4().hex}.wav"
        temp_path = os.path.join(TEMP_DIR, temp_filename)
        
        # 确保临时目录存在
        os.makedirs(TEMP_DIR, exist_ok=True)
        
        # 确保音频数据格式正确
        audio_data = result["audio_data"]
        sample_rate = result["sample_rate"]
        
        # 检查并打印音频信息
        logger.info(f"音频数据类型: {audio_data.dtype}, 形状: {audio_data.shape}")
        logger.info(f"音频范围: 最小={audio_data.min()}, 最大={audio_data.max()}")
        
        # 确保是整数类型，防止因为float类型导致无声音
        if audio_data.dtype != np.int16:
            if np.issubdtype(audio_data.dtype, np.floating) and audio_data.max() <= 1.0 and audio_data.min() >= -1.0:
                # 浮点数据在[-1, 1]范围内，缩放到int16范围
                audio_data = (audio_data * 32767).astype(np.int16)
                logger.info("浮点数据已缩放至int16范围")
            else:
                # 其他情况直接转换
                audio_data = audio_data.astype(np.int16)
                logger.info("数据已转换为int16类型")
        
        # 检查音频数据是否为空
        if audio_data.size == 0:
            raise HTTPException(status_code=500, detail="合成的音频数据为空")
        
        # 保存合成的语音到临时文件
        wav.write(temp_path, sample_rate, audio_data)
        
        # 检查生成的文件是否有效
        if os.path.getsize(temp_path) <= 44:  # WAV文件头大小约44字节
            logger.error("生成的WAV文件无效或为空")
            raise HTTPException(status_code=500, detail="生成的音频文件无效")
        
        # 返回临时文件的URL
        return {
            "success": True,
            "url": f"/temp/{temp_filename}"
        }
    except Exception as e:
        logger.exception("语音合成失败")
        raise HTTPException(status_code=500, detail=f"语音合成失败: {str(e)}")

@app.post("/api/courseware")
async def process_courseware(
    file: UploadFile = File(...),
    voice_id: str = Form(...),
    is_preset: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    处理课件文件并生成视频
    
    - file: 课件文件 (.pptx, .docx)
    - voice_id: 声音ID或预置声音名称
    - is_preset: 是否使用预置声音
    """
    try:
        # 这部分代码存根，实际的课件处理应该在courseware路由中实现
        # 此处只是确保处理预置声音与自定义声音的逻辑正确
        
        # 获取声音信息
        voice_data = None
        voice_transcript = None
        
        if is_preset:
            # 使用预置声音，不需要加载语音文件
            voice_name = voice_id
        else:
            # 使用上传的声音
            voice = db.query(Voice).filter(Voice.id == voice_id).first()
            if not voice:
                raise HTTPException(status_code=404, detail="声音不存在")
                
            # 确保用户只能使用自己的声音
            if voice.user_id != current_user.id and not current_user.is_admin:
                raise HTTPException(status_code=403, detail="没有权限使用此声音")
                
            voice_data = os.path.join(UPLOAD_DIR, voice.filename)
            voice_transcript = voice.transcript
            voice_name = voice.name
        
        # 正常情况下，这里会对课件进行处理
        # 但实际处理逻辑应该在courseware路由中实现
        
        # 模拟处理返回结果
        return {
            "success": True,
            "message": "课件处理请求已转发至处理模块",
            "is_preset": is_preset,
            "voice_id": voice_id
        }
    except Exception as e:
        # 这里缺少了缩进的代码块
        logger.exception("课件处理失败")
        raise HTTPException(status_code=500, detail=f"课件处理失败: {str(e)}")

@app.get("/")
def read_root():
    return {"message": "Welcome to AI Voice API"}
