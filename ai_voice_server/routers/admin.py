import os
from fastapi import APIRouter, Depends, HTTPException, status, Form, Body
from fastapi.security import OAuth2PasswordBearer
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from ..database import get_db
from ..models import models
from ..utils.security import get_current_user, get_password_hash
# 修改导入方式，直接导入schemas模块
import sys
import os.path
# 添加上层目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schemas import schemas

# 添加系统信息收集所需的库
import psutil
import time
import platform
from datetime import datetime, timedelta

router = APIRouter()

# 验证是否为管理员
async def verify_admin(current_user: models.User = Depends(get_current_user)):
    """检查用户是否具有管理员权限"""
    if not current_user:
        print(f"身份验证失败: 用户不存在")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未通过身份验证"
        )
    
    # 添加调试信息
    print(f"验证管理员权限: 用户 {current_user.username}, is_admin={current_user.is_admin}, 类型={type(current_user.is_admin)}")
    
    # 确保字段检查正确 - 增强健壮性
    if not hasattr(current_user, 'is_admin'):
        print(f"用户对象缺少is_admin属性")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，只有管理员可以访问此功能"
        )
        
    # 确保布尔值解析正确 - 使用特别的方法处理不同类型的值
    # 有些数据库驱动可能返回整数(0/1)而不是布尔值
    is_admin = False
    if isinstance(current_user.is_admin, bool):
        is_admin = current_user.is_admin
    elif isinstance(current_user.is_admin, int):
        is_admin = current_user.is_admin != 0
    else:
        # 最后尝试强制转换为布尔值
        is_admin = bool(current_user.is_admin)
    
    print(f"is_admin转换为布尔值: {is_admin}, 原始值: {current_user.is_admin}")
    
    if not is_admin:
        print(f"拒绝访问: 用户不是管理员")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，只有管理员可以访问此功能"
        )
    
    print(f"验证成功: 用户 {current_user.username} 是管理员")
    return current_user

# 检查管理员权限的端点
@router.get("/check")
async def check_admin_status(current_user: models.User = Depends(verify_admin)):
    """检查当前用户是否为管理员"""
    return {"is_admin": True, "username": current_user.username}

# 获取所有用户
@router.get("/users", response_model=List[schemas.UserInfo])
async def get_all_users(
    skip: int = 0, 
    limit: int = 100,
    current_user: models.User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    # 查询所有用户，并计算每个用户的声音和课件数量
    users = db.query(models.User).offset(skip).limit(limit).all()
    
    # 构建用户信息列表
    user_info_list = []
    for user in users:
        # 获取用户声音数量
        voice_count = db.query(func.count(models.Voice.id)).filter(models.Voice.user_id == user.id).scalar()
        
        # 获取用户课件数量
        courseware_count = db.query(func.count(models.Courseware.id)).filter(models.Courseware.user_id == user.id).scalar()
        
        # 创建UserInfo对象
        user_info = schemas.UserInfo(
            id=user.id,
            username=user.username,
            is_admin=user.is_admin,
            created_at=user.created_at,
            voice_count=voice_count,
            courseware_count=courseware_count
        )
        user_info_list.append(user_info)
    
    return user_info_list

# 创建新用户
@router.post("/users")
async def create_user(
    username: str = Form(...),
    password: str = Form(...),
    is_admin: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(verify_admin)
):
    # 检查用户名是否已存在
    existing_user = db.query(models.User).filter(models.User.username == username).first()
    if (existing_user):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被注册"
        )
    
    # 创建新用户
    hashed_password = get_password_hash(password)
    db_user = models.User(username=username, hashed_password=hashed_password, is_admin=is_admin)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return {
        "id": db_user.id,
        "username": db_user.username,
        "is_admin": db_user.is_admin,
        "created_at": db_user.created_at
    }

# 更新用户信息 - 修复422错误，支持Form格式数据
@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    username: str = Form(...),  # 使用Form从表单中获取数据
    password: Optional[str] = Form(None),  # 密码可选
    is_admin: str = Form("false"),  # 接收字符串格式的布尔值
    db: Session = Depends(get_db),
    current_user: models.User = Depends(verify_admin)
):
    # 处理is_admin字段 - 将字符串转换为布尔值
    # 接受多种可能的表示形式
    is_admin_bool = False
    if is_admin.lower() in ["true", "1", "yes", "y", "on"]:
        is_admin_bool = True
    
    print(f"更新用户 {user_id}: username={username}, is_admin={is_admin} -> {is_admin_bool}")
    
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名不能为空"
        )
        
    # 查找用户
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 检查用户名是否已被其他用户使用
    if username != db_user.username:
        existing_user = db.query(models.User).filter(models.User.username == username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已被其他用户使用"
            )

    # 更新用户信息
    db_user.username = username
    db_user.is_admin = is_admin_bool  # 使用转换后的布尔值
    
    # 如果提供了密码，则更新密码
    if password:
        db_user.hashed_password = get_password_hash(password)
    
    db.commit()
    db.refresh(db_user)
    
    return {
        "id": db_user.id,
        "username": db_user.username,
        "is_admin": db_user.is_admin,
        "created_at": db_user.created_at
    }

# 删除用户
@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(verify_admin)
):
    # 不能删除自己
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="管理员不能删除自己的账户"
        )
    
    # 检查是否为系统用户
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 阻止删除system用户
    if user.username == "system":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能删除系统用户"
        )
    
    # 删除用户前，先删除其关联的声音和课件
    voices = db.query(models.Voice).filter(models.Voice.user_id == user_id).all()
    for voice in voices:
        db.delete(voice)
    
    coursewares = db.query(models.Courseware).filter(models.Courseware.user_id == user_id).all()
    for courseware in coursewares:
        db.delete(courseware)
    
    # 删除用户
    db.delete(user)
    db.commit()
    return {"message": "用户及其关联数据已删除"}

# 获取声音列表
@router.get("/voices")
async def get_all_voices(
    skip: int = 0, 
    limit: int = 100,
    current_user: models.User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    # 修改查询，加载所有者信息
    voices = db.query(models.Voice).options(
        joinedload(models.Voice.owner)  # 使用导入的joinedload而不是orm.joinedload
    ).offset(skip).limit(limit).all()
    
    # 构造包含所有者信息的响应数据
    result = []
    for voice in voices:
        voice_data = {
            "id": voice.id,
            "name": voice.name,
            "filename": voice.filename,
            "transcript": voice.transcript,
            "user_id": voice.user_id,
            "is_preset": voice.is_preset,
            "created_at": voice.created_at,
            "owner_username": voice.owner.username if voice.owner else None
        }
        result.append(voice_data)
    
    return result

# 获取课件列表
@router.get("/coursewares", response_model=List[schemas.Courseware])
async def get_all_coursewares(
    skip: int = 0, 
    limit: int = 100,
    current_user: models.User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    coursewares = db.query(models.Courseware).offset(skip).limit(limit).all()
    return coursewares

# 删除声音
@router.delete("/voices/{voice_id}")
async def delete_voice(
    voice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(verify_admin)
):
    try:
        # 查找声音
        voice = db.query(models.Voice).filter(models.Voice.id == voice_id).first()
        if not voice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="声音不存在"
            )
        
        # 修复：检查是否为预置声音或系统用户声音
        system_user = db.query(models.User).filter(models.User.username == "system").first()
        
        if voice.is_preset or (voice.user_id == system_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="不能删除预置声音或系统用户的声音"
            )
            
        # 1. 先删除使用该声音的所有课件
        coursewares = db.query(models.Courseware).filter(models.Courseware.voice_id == voice_id).all()
        for courseware in coursewares:
            try:
                if (courseware.file_path and os.path.exists(courseware.file_path)):
                    os.remove(courseware.file_path)
                
                # 删除课件任务目录
                task_dir = os.path.dirname(courseware.file_path)
                if (os.path.exists(task_dir) and os.path.isdir(task_dir)):
                    import shutil
                    shutil.rmtree(task_dir)
            except Exception as e:
                print(f"Error removing courseware file/folder: {e}")
                
            db.delete(courseware)
            
        # 提交课件删除操作
        db.flush()
        
        # 2. 删除声音文件
        try:
            # 修复: 使用voice.filename而不是voice.file_path
            uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
            file_path = os.path.join(uploads_dir, voice.filename)
            if voice.filename and os.path.exists(file_path) and not voice.is_preset:
                os.remove(file_path)
                print(f"已删除声音文件: {file_path}")
        except Exception as e:
            print(f"Error removing voice file: {e}")
            
        # 3. 删除声音记录
        db.delete(voice)
        db.commit()
        
        return {"message": "声音及关联课件已成功删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error in delete_voice: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除声音失败: {str(e)}"
        )

# 新增 API 端点: 获取系统统计数据
@router.get("/stats")
async def get_system_stats(
    current_user: models.User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """获取系统的统计数据，包括用户数、声音数、课件数以及系统状态"""
    
    try:
        # 获取用户总数
        users_count = db.query(func.count(models.User.id)).scalar()
        
        # 获取声音总数
        voices_count = db.query(func.count(models.Voice.id)).scalar()
        
        # 获取课件总数
        coursewares_count = db.query(func.count(models.Courseware.id)).scalar()
        
        # 获取语音合成次数（从独立的语音合成记录表获取）
        voice_synthesis_count = db.query(func.count(models.SynthesisLog.id)).filter(
            models.SynthesisLog.type == "voice"
        ).scalar()
        
        # 获取课件合成次数
        courseware_synthesis_count = db.query(func.count(models.SynthesisLog.id)).filter(
            models.SynthesisLog.type == "courseware"
        ).scalar()
        
        # 获取系统状态信息
        cpu_usage = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 获取GPU显存信息
        gpu_memory = get_gpu_memory_info()
        
        system_status = {
            "cpu": {
                "usage": cpu_usage,
                "usage_str": f"{cpu_usage}%",
                "cores": psutil.cpu_count(logical=True),
                "physical_cores": psutil.cpu_count(logical=False)
            },
            "memory": {
                "usage": memory.percent,
                "usage_str": f"{memory.percent}%", 
                "used": memory.used,
                "used_str": f"{memory.used / (1024**3):.2f} GB",
                "total": memory.total,
                "total_str": f"{memory.total / (1024**3):.2f} GB"
            },
            "disk": {
                "usage": disk.percent,
                "usage_str": f"{disk.percent}%", 
                "used": disk.used,
                "used_str": f"{disk.used / (1024**3):.2f} GB",
                "total": disk.total,
                "total_str": f"{disk.total / (1024**3):.2f} GB"
            },
            "gpu_memory": gpu_memory,
            "uptime": get_system_uptime()
        }
        
        # 构建并返回统计数据
        stats = {
            "users_count": users_count,
            "voices_count": voices_count,
            "coursewares_count": coursewares_count,
            "voice_synthesis_count": voice_synthesis_count,
            "courseware_synthesis_count": courseware_synthesis_count,
            "total_synthesis_count": voice_synthesis_count + courseware_synthesis_count,
            "system_status": system_status,
            "timestamp": datetime.now().isoformat()
        }
        
        return stats
    except Exception as e:
        print(f"获取系统统计数据时出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统统计数据失败: {str(e)}"
        )

# 新增端点: 获取系统资源实时数据，用于图表显示
@router.get("/system-monitor")
async def get_system_monitor(
    current_user: models.User = Depends(verify_admin)
):
    """获取系统资源的实时监控数据"""
    try:
        # 获取系统资源使用率
        cpu_usage = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 获取GPU显存使用率
        gpu_memory = get_gpu_memory_info()
        gpu_usage = gpu_memory["usage"] if gpu_memory else 0
        
        # 构建监控数据
        monitor_data = {
            "timestamp": datetime.now().isoformat(),
            "cpu_usage": cpu_usage,
            "memory_usage": memory.percent,
            "disk_usage": disk.percent,
            "gpu_usage": gpu_usage
        }
        
        return monitor_data
    except Exception as e:
        print(f"获取系统监控数据时出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取系统监控数据失败: {str(e)}"
        )

# 辅助函数: 获取GPU显存信息
def get_gpu_memory_info():
    """获取GPU显存使用情况，支持NVIDIA GPU"""
    try:
        # 尝试使用nvidia-smi命令获取GPU信息
        import subprocess
        result = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,memory.total', '--format=csv,nounits,noheader'], 
                                stdout=subprocess.PIPE, 
                                universal_newlines=True)
        
        if result.returncode != 0:
            print("无法使用nvidia-smi获取GPU信息")
            return {
                "available": False,
                "message": "系统未安装NVIDIA驱动或无法访问GPU"
            }
        
        # 解析输出
        output = result.stdout.strip().split('\n')
        if not output or not output[0].strip():
            return {
                "available": False,
                "message": "未检测到GPU设备"
            }
        
        gpu_info = []
        
        for i, line in enumerate(output):
            if not line.strip():
                continue
                
            try:
                memory_used, memory_total = map(int, line.split(','))
                usage_percent = (memory_used / memory_total) * 100 if memory_total > 0 else 0
                
                gpu_info.append({
                    "index": i,
                    "memory_used": memory_used,
                    "memory_used_str": f"{memory_used} MB",
                    "memory_total": memory_total,
                    "memory_total_str": f"{memory_total} MB",
                    "usage": usage_percent,
                    "usage_str": f"{usage_percent:.1f}%"
                })
            except Exception as e:
                print(f"解析GPU {i} 信息失败: {e}")
                continue
        
        # 计算总体GPU使用率（所有GPU的平均值）
        if gpu_info:
            total_usage = sum(gpu['usage'] for gpu in gpu_info) / len(gpu_info)
            total_memory_used = sum(gpu['memory_used'] for gpu in gpu_info)
            total_memory_total = sum(gpu['memory_total'] for gpu in gpu_info)
        else:
            total_usage = 0
            total_memory_used = 0
            total_memory_total = 0
            
        return {
            "available": True,
            "gpu_count": len(gpu_info),
            "gpus": gpu_info,
            "usage": total_usage,
            "usage_str": f"{total_usage:.1f}%",
            "memory_used": total_memory_used,
            "memory_used_str": f"{total_memory_used} MB",
            "memory_total": total_memory_total,
            "memory_total_str": f"{total_memory_total} MB"
        }
    except Exception as e:
        print(f"获取GPU显存信息失败: {e}")
        return {
            "available": False,
            "message": f"获取GPU信息时出错: {str(e)}"
        }

# 辅助函数: 获取系统运行时间
def get_system_uptime():
    """获取系统运行时间，格式化为人类可读的形式"""
    try:
        # 获取当前时间
        current_time = time.time()
        
        # 获取系统启动时间
        boot_time = psutil.boot_time()
        
        # 计算运行时间（秒）
        uptime_seconds = current_time - boot_time
        
        # 转换为天、小时、分钟
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        
        # 格式化输出
        if days > 0:
            return f"{days}天 {hours}小时"
        elif hours > 0:
            return f"{hours}小时 {minutes}分钟"
        else:
            return f"{minutes}分钟"
    except Exception as e:
        print(f"获取系统运行时间出错: {e}")
        return "未知"

# 新增 API 端点: 获取用户增长统计数据
@router.get("/user-growth-stats")
async def get_user_growth_stats(
    current_user: models.User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """获取用户增长统计数据"""
    try:
        # 获取最近30天的用户注册数据
        thirty_days_ago = datetime.now() - timedelta(days=30)
        daily_registrations = db.query(
            func.date(models.User.created_at).label('date'),
            func.count(models.User.id).label('count')
        ).filter(
            models.User.created_at >= thirty_days_ago
        ).group_by(
            func.date(models.User.created_at)
        ).all()
        
        # 计算每日增长率
        growth_data = []
        for i in range(len(daily_registrations)):
            current_day = daily_registrations[i]
            if i == 0:
                growth_rate = 0
            else:
                prev_day = daily_registrations[i-1]
                growth_rate = ((current_day.count - prev_day.count) / prev_day.count * 100) if prev_day.count > 0 else 0
            
            growth_data.append({
                "date": current_day.date.isoformat(),
                "new_users": current_day.count,
                "growth_rate": round(growth_rate, 2)
            })
        
        return growth_data
    except Exception as e:
        print(f"获取用户增长统计数据时出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户增长统计数据失败: {str(e)}"
        )

# 新增 API 端点: 获取用户身份统计数据
@router.get("/user-role-stats")
async def get_user_role_stats(
    current_user: models.User = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """获取用户身份统计数据"""
    try:
        # 获取各身份用户数量
        role_stats = db.query(
            models.User.user_role,
            func.count(models.User.id).label('count')
        ).filter(
            models.User.user_role.isnot(None)
        ).group_by(
            models.User.user_role
        ).all()
        
        # 计算总数
        total_users = sum(stat.count for stat in role_stats)
        
        # 构建统计数据
        stats_data = []
        for stat in role_stats:
            percentage = (stat.count / total_users * 100) if total_users > 0 else 0
            stats_data.append({
                "role": stat.user_role,
                "count": stat.count,
                "percentage": round(percentage, 2)
            })
        
        return stats_data
    except Exception as e:
        print(f"获取用户身份统计数据时出错: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户身份统计数据失败: {str(e)}"
        )
