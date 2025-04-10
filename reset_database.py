#!/usr/bin/env python3
"""
重置数据库脚本：删除所有表并重新创建数据库结构，同时清理本地文件
"""

import os
import sys
import logging
import shutil
from sqlalchemy import text

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_voice_server.database import engine, SessionLocal
from ai_voice_server.models.models import Base

# 设置日志级别
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定义需要清理的目录 - 修正路径
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_voice_server", "uploads")
COURSEWARE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_voice_server", "coursewares")
TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_voice_server", "temp")

def clean_directory(directory_path):
    """清空目录中的所有文件和子目录，但保留目录本身"""
    if not os.path.exists(directory_path):
        logger.info(f"目录不存在，创建: {directory_path}")
        os.makedirs(directory_path, exist_ok=True)
        return True
        
    try:
        # 检查路径安全性，确保只删除项目内的目录
        project_root = os.path.dirname(os.path.abspath(__file__))
        if not directory_path.startswith(project_root):
            logger.error(f"安全检查：拒绝清理项目外的目录: {directory_path}")
            return False
            
        # 列出目录内容
        for item in os.listdir(directory_path):
            item_path = os.path.join(directory_path, item)
            
            # 跳过.gitkeep文件（如果存在）
            if item == ".gitkeep":
                continue
                
            try:
                if os.path.isdir(item_path):
                    logger.info(f"删除目录: {item_path}")
                    shutil.rmtree(item_path)
                else:
                    logger.info(f"删除文件: {item_path}")
                    os.unlink(item_path)
            except Exception as e:
                logger.error(f"删除 {item_path} 时出错: {e}")
                
        logger.info(f"已清空目录: {directory_path}")
        return True
    except Exception as e:
        logger.error(f"清理目录 {directory_path} 时出错: {e}")
        return False

def reset_database():
    """删除所有表并重新创建，并清理相关文件"""
    try:
        # 获取数据库连接
        with engine.connect() as connection:
            # 获取所有表名
            result = connection.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result]
            
            if tables:
                logger.info(f"找到 {len(tables)} 个表: {', '.join(tables)}")
                
                # 暂时禁用外键约束检查
                connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
                
                # 删除所有表
                for table in tables:
                    logger.info(f"删除表: {table}")
                    connection.execute(text(f"DROP TABLE IF EXISTS {table}"))
                
                # 重新启用外键约束检查
                connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                
                logger.info("已删除所有表")
            else:
                logger.info("数据库中没有表")
            
            # 提交事务
            connection.commit()
        
        # 使用模型定义重新创建所有表
        logger.info("重新创建所有表")
        Base.metadata.create_all(bind=engine)
        logger.info("数据库结构已重新创建")
        
        # 清理上传的文件和课件文件
        logger.info("开始清理本地文件...")
        clean_directory(UPLOAD_DIR)
        clean_directory(COURSEWARE_DIR)
        clean_directory(TEMP_DIR)
        logger.info("本地文件清理完成")
        
        return True
    except Exception as e:
        logger.error(f"重置数据库时出错: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="重置数据库、清理文件并重新创建表结构")
    parser.add_argument('--confirm', action='store_true', help='确认删除数据库内容和上传的文件')
    parser.add_argument('--keep-files', action='store_true', help='保留本地文件，只重置数据库')
    args = parser.parse_args()
    
    if not args.confirm:
        print("警告: 此操作将删除数据库中的所有数据以及所有上传的文件!")
        print("如果确定要继续，请添加 --confirm 参数")
        print("如果仅想重置数据库但保留文件，请添加 --keep-files 参数")
        sys.exit(1)
    
    # 如果指定了保留文件，输出消息
    if args.keep_files:
        print("将只重置数据库，保留本地文件")
    
    if reset_database():
        # 如果成功重置数据库但需要保留文件
        if args.keep_files:
            print("数据库已成功重置，本地文件已保留。")
        else:
            print("数据库已成功重置，本地文件已清理。")
        
        print("您可以现在运行 import_preset_voices.py 来导入预置声音。")
        
        # 询问是否立即导入预置声音
        response = input("是否立即导入预置声音? (y/n): ")
        if response.lower() == 'y':
            try:
                from import_preset_voices import import_preset_voices
                print("正在导入预置声音...")
                import_preset_voices()
            except Exception as e:
                print(f"导入预置声音时出错: {e}")
    else:
        print("重置数据库失败")
