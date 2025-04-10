#!/usr/bin/env python3
"""
导入预置声音到数据库
"""

import os
import sys
import logging
import argparse
import json
from sqlalchemy import text
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_voice_server.database import engine, SessionLocal
from ai_voice_server.models.models import Voice, User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def import_preset_voices(noinit=False):
    """导入预置声音到数据库"""
    logger.info("正在导入预置声音...")
    
    # 初始化CosyVoice模型获取预置声音列表
    from ai_voice_server.cosyvoice_helper import CosyVoiceHelper
    cosyvoice_helper = CosyVoiceHelper(lazy_load=noinit)
    
    # 获取预置声音列表 - 应该通过代码动态获取，而不是硬编码
    if noinit:
        # 如果使用--noinit参数，则仍然需要初始化模型来获取声音列表
        # 因为声音列表必须从模型获取，而不是硬编码的
        cosyvoice_helper._initialize_model()
    
    preset_voices = cosyvoice_helper.get_preset_voices()
    
    if not preset_voices:
        logger.error("无法获取预置声音列表，请检查模型是否正确加载")
        return
    
    logger.info(f"找到 {len(preset_voices)} 个预置声音: {preset_voices}")
    
    # 获取数据库会话
    db = SessionLocal()
    
    try:
        # 检查是否已有系统用户
        admin_user = db.query(User).filter(User.username == "system").first()
        
        if not admin_user:
            # 创建系统用户用于预置声音
            admin_user = User(
                username="system",
                hashed_password="$2b$12$NotARealHash",  # 不可用于登录的哈希
                is_admin=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            logger.info("创建了系统用户用于预置声音")
        
        # 为每个预置声音创建记录
        for voice_name in preset_voices:
            # 检查声音是否已存在
            existing_voice = db.query(Voice).filter(
                Voice.name == voice_name,
                Voice.is_preset == True
            ).first()
            
            if not existing_voice:
                # 创建新的预置声音记录
                new_voice = Voice(
                    name=voice_name,
                    filename="preset",  # 预置声音没有文件名
                    transcript="",  # 预置声音没有文本
                    user_id=admin_user.id,  # 确保关联到系统用户
                    is_preset=True
                )
                db.add(new_voice)
                logger.info(f"添加预置声音: {voice_name}")
            elif existing_voice.user_id != admin_user.id:
                # 如果已存在但未关联到系统用户，则更新关联
                existing_voice.user_id = admin_user.id
                logger.info(f"更新预置声音所有者: {voice_name}")
        
        # 提交更改
        db.commit()
        logger.info("预置声音导入完成")
        
        # 检查导入结果
        preset_voices_count = db.query(Voice).filter(Voice.is_preset == True).count()
        logger.info(f"当前数据库中有 {preset_voices_count} 个预置声音")
        
        # 检查预置声音的所有权
        system_owned = db.query(Voice).filter(
            Voice.is_preset == True,
            Voice.user_id == admin_user.id
        ).count()
        
        if system_owned < preset_voices_count:
            logger.warning(f"有 {preset_voices_count - system_owned} 个预置声音不属于系统用户")
            
            # 修复预置声音的所有权
            db.query(Voice).filter(
                Voice.is_preset == True,
                Voice.user_id != admin_user.id
            ).update({"user_id": admin_user.id})
            db.commit()
            logger.info("已修复预置声音的所有权")
    
    finally:
        db.close()

if __name__ == "__main__":
    # 添加命令行参数解析
    parser = argparse.ArgumentParser(description="导入预置声音到数据库")
    parser.add_argument('--noinit', action='store_true', help='懒加载模式(仍会初始化模型以获取声音列表)')
    args = parser.parse_args()
    
    import_preset_voices(args.noinit)
