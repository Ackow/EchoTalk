"""注册、登录、退出、改密、头像和当前账户接口（控制器层）。

只负责解析请求、调用服务层、格式化响应，不含业务逻辑。
"""
from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_session, get_current_user
from app.core.database import get_db
from app.core.errors import AppError
from app.models import AuthSession, User
from app.schemas.auth import AuthResponse, Credentials, PasswordChange, UserResponse
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


@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChange,
    session: AuthSession = Depends(get_current_session),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改密码：当前设备保持登录，其余设备上的会话全部失效。"""
    auth_service.change_password(db, user, payload.current_password, payload.new_password, session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/avatar", status_code=status.HTTP_201_CREATED)
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传/替换头像：jpg / png / webp，上限 2 MB。"""
    relative = auth_service.set_avatar(db, user, file.filename, await file.read())
    return {"avatar_path": relative}


@router.get("/avatar/{user_id}")
def get_avatar(user_id: int, db: Session = Depends(get_db)):
    """读取头像：无需登录，侧栏与页面直接以 <img> 引用（URL 带随机串，可长缓存）。"""
    path = auth_service.avatar_file(db, user_id)
    if path is None:
        raise AppError("该账户未设置头像", code="AVATAR_NOT_FOUND", status_code=404)
    return FileResponse(path, headers={"Cache-Control": "public, max-age=86400"})


@router.delete("/avatar")
def remove_avatar(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """移除头像：文件删除，前端回落到用户名首字母。"""
    return {"removed": auth_service.remove_avatar(db, user)}
