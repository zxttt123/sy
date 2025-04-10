from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str
    is_admin: bool = False

class UserBase(BaseModel):
    username: str
    # 新增可选字段
    user_role: Optional[str] = None
    email: Optional[str] = None
    organization: Optional[str] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_admin: bool = False
    created_at: datetime

    class Config:
        orm_mode = True

# 添加 UserInfo 类，用于管理员查看用户信息
class UserInfo(BaseModel):
    id: int
    username: str
    is_admin: bool
    created_at: datetime
    voice_count: int = 0
    courseware_count: int = 0
    # 新增字段
    user_role: Optional[str] = None
    email: Optional[str] = None
    organization: Optional[str] = None

    class Config:
        orm_mode = True

# 新增个人资料更新模型
class UserProfile(BaseModel):
    user_role: Optional[str] = None
    email: Optional[str] = None
    organization: Optional[str] = None

    class Config:
        orm_mode = True

# 新增密码修改模型
class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class Voice(BaseModel):
    id: int
    name: str
    filename: Optional[str] = None
    transcript: Optional[str] = None
    user_id: int
    is_preset: bool = False
    created_at: datetime

    class Config:
        orm_mode = True

class CoursewareBase(BaseModel):
    task_id: str
    status: str

class CoursewareCreate(CoursewareBase):
    file_path: Optional[str] = None
    user_id: int
    voice_id: int
    original_filename: Optional[str] = None
    process_date: Optional[str] = None
    animation_mode: Optional[str] = "dynamic"  # 添加动画模式字段，默认为动态模式
    transition_time: Optional[float] = 0.5  # 过渡时间，默认0.5秒

class Courseware(CoursewareBase):
    id: int
    file_path: Optional[str] = None
    user_id: int
    voice_id: int
    created_at: datetime
    updated_at: datetime
    original_filename: Optional[str] = None
    process_date: Optional[str] = None
    animation_mode: Optional[str] = "dynamic"  # 添加动画模式字段
    transition_time: Optional[float] = 0.5  # 过渡时间

    class Config:
        orm_mode = True

# 更新系统状态数据模型
class SystemCpuStatus(BaseModel):
    usage: float
    usage_str: str
    cores: int
    physical_cores: int

class SystemMemoryStatus(BaseModel):
    usage: float
    usage_str: str
    used: int
    used_str: str
    total: int
    total_str: str

class SystemDiskStatus(BaseModel):
    usage: float
    usage_str: str
    used: int
    used_str: str
    total: int
    total_str: str

# 添加GPU显存数据模型
class GpuInfo(BaseModel):
    index: int
    memory_used: int
    memory_used_str: str
    memory_total: int
    memory_total_str: str
    usage: float
    usage_str: str

class GpuMemoryStatus(BaseModel):
    available: bool
    gpu_count: Optional[int] = None
    gpus: Optional[List[GpuInfo]] = None
    usage: Optional[float] = None
    usage_str: Optional[str] = None
    memory_used: Optional[int] = None
    memory_used_str: Optional[str] = None
    memory_total: Optional[int] = None
    memory_total_str: Optional[str] = None
    message: Optional[str] = None

class SystemStatus(BaseModel):
    cpu: SystemCpuStatus
    memory: SystemMemoryStatus
    disk: SystemDiskStatus
    gpu_memory: GpuMemoryStatus
    uptime: str

# 系统统计数据模型
class SystemStats(BaseModel):
    users_count: int
    voices_count: int
    coursewares_count: int
    voice_synthesis_count: int
    courseware_synthesis_count: int
    total_synthesis_count: int
    system_status: SystemStatus
    timestamp: str

# 系统监控数据模型（用于实时图表）
class SystemMonitor(BaseModel):
    timestamp: str
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    gpu_usage: float
