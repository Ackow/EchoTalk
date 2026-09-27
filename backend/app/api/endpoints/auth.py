"""注册、登录、退出和当前账户接口（控制器层）。

只负责解析请求、调用服务层、格式化响应，不含业务逻辑。
"""
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_session, get_current_user
from app.core.database import get_db
from app.models import AuthSession, User
from app.schemas import AuthResponse, Credentials, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["账户"])  # 本模块所有接口挂在 /api/auth 下


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: Credentials, db: Session = Depends(get_db)):
    """注册成功后立即签发本设备会话。"""
    user, token = auth_service.register(db, payload.username, payload.password)
    return AuthResponse(access_token=token, user=user)


@router.post("/login", response_model=AuthResponse)
def login(payload: Credentials, db: Session = Depends(get_db)):
    """密码验证通过后建立新的独立登录会话。"""
    user, token = auth_service.login(db, payload.username, payload.password)
    return AuthResponse(access_token=token, user=user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(session: AuthSession = Depends(get_current_session), db: Session = Depends(get_db)):
    """退出只撤销本次请求持有的会话令牌。"""
    auth_service.revoke_session(db, session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):  # 依赖链：令牌 → 会话 → 用户
    return user
