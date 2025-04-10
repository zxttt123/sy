from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, DateTime, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime

# 导入Base而不是重新定义
from ..database import Base

class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    hashed_password = Column(String(100))
    # 明确布尔值转换
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # 新增字段
    user_role = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    organization = Column(String(100), nullable=True)

    # 关系: 一个用户可以有多个声音
    voices = relationship("Voice", back_populates="owner")
    coursewares = relationship("Courseware", back_populates="user")
    synthesis_logs = relationship("SynthesisLog", back_populates="user")

class Voice(Base):
    """声音模型"""
    __tablename__ = "voices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    filename = Column(String(255))  # 保存文件名，不是路径
    transcript = Column(String(1000))  # 提示文本字段
    user_id = Column(Integer, ForeignKey("users.id"))
    is_preset = Column(Boolean, default=False)  # 添加预置声音标志
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 修正关系定义，确保字段名称一致性
    owner = relationship("User", back_populates="voices", foreign_keys=[user_id])
    coursewares = relationship("Courseware", back_populates="voice")
    synthesis_logs = relationship("SynthesisLog", back_populates="voice")

class Courseware(Base):
    """课件模型"""
    __tablename__ = "coursewares"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(50), unique=True, index=True)
    file_path = Column(String(255), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    voice_id = Column(Integer, ForeignKey("voices.id"))
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 新增字段存储原始文件名和处理日期
    original_filename = Column(String(255), nullable=True)
    process_date = Column(String(10), nullable=True)  # YYYYMMDD格式
    
    # 新增字段处理PPT动态切换效果
    animation_mode = Column(String(20), default="dynamic")  # dynamic 或 static
    transition_time = Column(Float, default=0.5)  # 过渡时间，单位秒
    
    # 关系
    user = relationship("User", back_populates="coursewares")
    voice = relationship("Voice", back_populates="coursewares")

class SynthesisLog(Base):
    """合成记录模型"""
    __tablename__ = "synthesis_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(20), index=True)  # "voice" 或 "courseware"
    user_id = Column(Integer, ForeignKey("users.id"))
    voice_id = Column(Integer, ForeignKey("voices.id"))
    text_length = Column(Integer, nullable=True)  # 合成的文本长度
    duration = Column(Float, nullable=True)  # 合成的音频时长（秒）
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关系
    user = relationship("User", back_populates="synthesis_logs")
    voice = relationship("Voice", back_populates="synthesis_logs")