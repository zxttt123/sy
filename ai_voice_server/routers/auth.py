# ai_voice_server/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException, status, Form, Body
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import timedelta
import sys
import os.path
from jose import JWTError, jwt
from typing import Optional

# 添加上层目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schemas import schemas
from ..database import get_db
from ..models import models
from ..utils.security import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    verify_password,
    SECRET_KEY,
    ALGORITHM
)

router = APIRouter()

# 设置 ACCESS_TOKEN_EXPIRE_MINUTES
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时

# OAuth2PasswordBearer需要提供tokenUrl
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")

# 定义get_current_user函数
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    通过Token获取当前用户
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# 定义一个可选的current_user_id函数用于前端不需要强制登录的场景
def get_current_user_id_optional(token: Optional[str] = None, db: Session = Depends(get_db)):
    """
    可选的获取当前用户ID函数，用于前端不强制登录的场景
    """
    if not token:
        return None
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None
    
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        return None
    return user.id

@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    用户登录，获取访问令牌
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # 确保包含管理员信息到token中
    access_token = create_access_token(
        data={"sub": user.username, "admin": user.is_admin},
        expires_delta=access_token_expires
    )
    
    # 明确返回is_admin标志
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "is_admin": user.is_admin
    }

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    username: str = Form(...),
    password: str = Form(...),
    user_role: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    organization: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    用户注册 - 扩展以接收新字段
    """
    # 检查用户是否已存在
    db_user = db.query(models.User).filter(models.User.username == username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被注册"
        )
    
    # 验证用户角色 (如果提供)
    valid_roles = ["学生", "教师", "研究人员", "其他"]
    if user_role and user_role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的用户身份，有效选项为: {', '.join(valid_roles)}"
        )
    
    # 创建新用户
    hashed_password = get_password_hash(password)
    db_user = models.User(
        username=username, 
        hashed_password=hashed_password,
        user_role=user_role,
        email=email,
        organization=organization
    )
    
    # 检查是否存在普通（非系统）用户，如果不存在，则设置为管理员
    regular_user_count = db.query(func.count(models.User.id)).filter(
        models.User.username != "system"  # 排除系统用户
    ).scalar()
    
    print(f"注册新用户: {username}, 现有普通用户数量: {regular_user_count}")
    
    if regular_user_count == 0:
        print(f"这是第一个普通用户，将 {username} 设置为管理员")
        db_user.is_admin = True
        print(f"设置后is_admin值: {db_user.is_admin}, 类型: {type(db_user.is_admin)}")
    
    db.add(db_user)
    db.commit()
    
    # 重新加载以确认设置成功
    db.refresh(db_user)
    print(f"提交后is_admin值: {db_user.is_admin}, 类型: {type(db_user.is_admin)}")
    
    # 返回响应，包含管理员标志和新增字段
    return {
        "message": "注册成功", 
        "username": username, 
        "is_admin": bool(db_user.is_admin),
        "user_role": db_user.user_role,
        "email": db_user.email,
        "organization": db_user.organization
    }

# 新增个人资料接口
@router.get("/users/profile", response_model=schemas.UserProfile)
async def get_user_profile(current_user: models.User = Depends(get_current_user)):
    """获取当前用户的个人资料"""
    return {
        "user_role": current_user.user_role,
        "email": current_user.email,
        "organization": current_user.organization
    }

# 修改个人资料接口 - 接收Form数据
@router.put("/users/profile", status_code=status.HTTP_200_OK)
async def update_user_profile(
    user_role: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    organization: Optional[str] = Form(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新当前用户的个人资料"""
    # 验证用户角色 (如果提供)
    valid_roles = ["学生", "教师", "研究人员", "其他"]
    if user_role and user_role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的用户身份，有效选项为: {', '.join(valid_roles)}"
        )
    
    # 更新字段
    if user_role is not None:
        current_user.user_role = user_role
    if email is not None:
        current_user.email = email
    if organization is not None:
        current_user.organization = organization
    
    db.commit()
    return {"status": "success", "message": "个人资料更新成功"}

# 修改密码接口 - 接收Form数据
@router.put("/users/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """修改当前用户的密码"""
    # 验证当前密码是否正确
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前密码不正确"
        )
    
    # 更新密码
    current_user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    return {"status": "success", "message": "密码修改成功"}