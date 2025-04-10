"""
音频识别和处理工具，用于语音识别和处理
"""

import os
import sys
import logging
import subprocess
import json
import tempfile
from typing import List, Dict, Any, Optional, Tuple, Union

import numpy as np
import ffmpeg

logger = logging.getLogger(__name__)

# 检查是否安装了whisper
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("未安装whisper模块，语音识别功能将不可用")

class AudioRecognizer:
    """
    使用whisper的语音识别模块
    """
    _instance = None
    
    def __new__(cls, model_size="medium"):
        if cls._instance is None:
            cls._instance = super(AudioRecognizer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self, model_size="medium"):
        """
        初始化语音识别器
        
        参数:
            model_size: 模型大小，可选 tiny, base, small, medium, large
        """
        if self._initialized:
            return
            
        if not WHISPER_AVAILABLE:
            raise ImportError("未安装whisper模块，无法初始化语音识别器")
            
        self.model_size = model_size
        self.model = None
        self._initialized = True
        
    def ensure_model_loaded(self):
        """确保模型已经加载"""
        if self.model is None:
            logger.info(f"加载Whisper {self.model_size}模型...")
            try:
                self.model = whisper.load_model(self.model_size)
                logger.info("Whisper模型加载完成")
            except Exception as e:
                logger.error(f"加载Whisper模型失败: {e}")
                raise
    
    def transcribe(self, audio_path: str, language: Optional[str] = "zh") -> Dict[str, Any]:
        """
        转录音频文件
        
        参数:
            audio_path: 音频文件路径
            language: 语言代码，如"zh"表示中文，"en"表示英文，None表示自动检测
            
        返回:
            转录结果，包含文本、分段、时间戳等信息
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
            
        self.ensure_model_loaded()
        
        try:
            logger.info(f"开始转录音频: {audio_path}")
            options = {
                "verbose": False,
            }
            
            if language:
                options["language"] = language
                
            result = self.model.transcribe(audio_path, **options)
            
            logger.info("转录完成")
            return result
        except Exception as e:
            logger.error(f"转录音频失败: {e}")
            raise
    
    def get_segments_with_timestamps(self, audio_path: str, language: Optional[str] = "zh") -> List[Dict[str, Any]]:
        """
        获取带时间戳的分段文本
        
        参数:
            audio_path: 音频文件路径
            language: 语言代码
            
        返回:
            包含时间戳和文本的分段列表
        """
        result = self.transcribe(audio_path, language)
        
        segments = []
        for segment in result.get("segments", []):
            segments.append({
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"].strip()
            })
            
        return segments

def convert_audio_to_wav(audio_path: str, output_path: Optional[str] = None) -> str:
    """
    将音频转换为WAV格式
    
    参数:
        audio_path: 输入音频路径
        output_path: 输出WAV文件路径，如果为None则自动生成
        
    返回:
        WAV文件路径
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
    if not output_path:
        fd, output_path = tempfile.mkstemp(suffix='.wav')
        os.close(fd)
    
    try:
        cmd = [
            "ffmpeg",
            "-i", audio_path,
            "-acodec", "pcm_s16le",  # 设置为16位PCM编码
            "-ac", "1",              # 设置为单声道
            "-ar", "16000",          # 设置采样率为16kHz
            "-y",                    # 覆盖已有文件
            output_path
        ]
        
        logger.info(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"转换成功: {output_path}")
            return output_path
        else:
            raise RuntimeError("转换失败，输出文件不存在或为空")
    
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8', errors='replace') if e.stderr else str(e)
        logger.error(f"转换音频失败: {error_msg}")
        raise RuntimeError(f"转换音频失败: {error_msg}")
    except Exception as e:
        logger.error(f"转换音频过程中发生错误: {str(e)}")
        raise

def get_audio_duration(file_path: str) -> float:
    """
    获取音频/视频文件的时长（秒）
    
    参数:
        file_path: 文件路径
    
    返回:
        文件时长（秒）
    """
    try:
        # 首先尝试使用sf.read获取音频时长
        try:
            import soundfile as sf
            data, sample_rate = sf.read(file_path)
            duration = len(data) / sample_rate
            logger.debug(f"音频文件 {os.path.basename(file_path)} 时长: {duration:.2f}秒")
            return duration
        except Exception:
            # 如果失败，尝试使用ffmpeg
            probe = ffmpeg.probe(file_path)
            # 获取音频或视频流
            stream = next((stream for stream in probe['streams'] if stream['codec_type'] in ['audio', 'video']), None)
            if stream:
                duration = float(stream.get('duration', 0))
                logger.debug(f"文件 {os.path.basename(file_path)} 时长: {duration:.2f}秒")
                return duration
        return 0
    except Exception as e:
        logger.error(f"获取文件时长失败: {str(e)}")
        return 0
