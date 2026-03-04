"""
Web API 路由
提供前端界面所需的 RESTful API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import secrets

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.session import get_db
from models.schedule import Schedule
from models.contact import Contact
from models.module_subscription import ModuleSubscription as Subscription

router = APIRouter(prefix="/api", tags=["api"])
security = HTTPBearer(auto_error=False)

# ============================================
# 临时用户系统（简化版，后续可接入数据库）
# ============================================

# 临时存储用户和 token
_temp_users = {}  # username -> {password, id}
_temp_tokens = {}  # token -> user_id
_bind_tokens = {}  # bind_token -> user_id

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """获取当前用户 ID"""
    if not credentials:
        raise HTTPException(status_code=401, detail="未登录")
    token = credentials.credentials
    user_id = _temp_tokens.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token 无效")
    return user_id


# ============================================
# 认证相关
# ============================================

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    token: str
    user: dict

@router.post("/auth/login", response_model=AuthResponse)
async def login(data: LoginRequest):
    """登录"""
    user = _temp_users.get(data.username)
    if not user or user["password"] != data.password:
        raise HTTPException(status_code=400, detail="用户名或密码错误")

    token = secrets.token_hex(16)
    _temp_tokens[token] = user["id"]

    return AuthResponse(
        token=token,
        user={"id": user["id"], "username": data.username}
    )

@router.post("/auth/register", response_model=AuthResponse)
async def register(data: RegisterRequest):
    """注册"""
    if data.username in _temp_users:
        raise HTTPException(status_code=400, detail="用户名已存在")

    user_id = f"user_{secrets.token_hex(8)}"
    _temp_users[data.username] = {
        "id": user_id,
        "password": data.password
    }

    token = secrets.token_hex(16)
    _temp_tokens[token] = user_id

    return AuthResponse(
        token=token,
        user={"id": user_id, "username": data.username}
    )

@router.get("/auth/wechat/bind")
async def get_wechat_bind_url(user_id: str = Depends(get_current_user)):
    """获取微信绑定二维码"""
    bind_token = secrets.token_hex(16)
    _bind_tokens[bind_token] = user_id

    # 这里应该生成带 bind_token 的二维码 URL
    # 简化处理，实际需要调用微信接口
    return {
        "qr_url": f"weixin://bind/{bind_token}",
        "bind_token": bind_token
    }

@router.get("/auth/wechat/check/{bind_token}")
async def check_wechat_bind(bind_token: str):
    """检查微信绑定状态"""
    # 简化处理，实际需要检查数据库
    bound = bind_token not in _bind_tokens
    return {"bound": bound}


# ============================================
# 日程相关
# ============================================

class ScheduleCreate(BaseModel):
    title: str
    scheduled_time: str
    description: Optional[str] = None

class ScheduleUpdate(BaseModel):
    title: Optional[str] = None
    scheduled_time: Optional[str] = None
    description: Optional[str] = None

class ScheduleResponse(BaseModel):
    id: int
    title: str
    scheduled_time: str
    description: Optional[str]
    created_at: str

@router.get("/schedules", response_model=List[ScheduleResponse])
async def list_schedules(
    date: Optional[str] = None,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取日程列表"""
    query = select(Schedule).where(Schedule.user_id == user_id)

    if date:
        # 筛选特定日期
        query = query.where(Schedule.scheduled_time >= f"{date} 00:00:00")
        query = query.where(Schedule.scheduled_time < f"{date} 23:59:59")

    query = query.order_by(Schedule.scheduled_time)
    result = await db.execute(query)
    schedules = result.scalars().all()

    return [
        ScheduleResponse(
            id=s.id,
            title=s.title,
            scheduled_time=s.scheduled_time.strftime("%Y-%m-%d %H:%M"),
            description=s.description,
            created_at=s.created_at.strftime("%Y-%m-%d %H:%M:%S")
        )
        for s in schedules
    ]

@router.post("/schedules", response_model=ScheduleResponse)
async def create_schedule(
    data: ScheduleCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建日程"""
    # 验证时间字段
    if not data.scheduled_time:
        raise HTTPException(status_code=400, detail="请选择日程时间")

    try:
        # 支持多种日期格式
        scheduled_time = None
        for fmt in ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"]:
            try:
                scheduled_time = datetime.strptime(data.scheduled_time, fmt)
                break
            except ValueError:
                continue

        if not scheduled_time:
            raise ValueError("无法解析日期格式")

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"日期格式错误: {str(e)}")

    schedule = Schedule(
        user_id=user_id,
        title=data.title,
        scheduled_time=scheduled_time,
        description=data.description
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)

    return ScheduleResponse(
        id=schedule.id,
        title=schedule.title,
        scheduled_time=schedule.scheduled_time.strftime("%Y-%m-%d %H:%M"),
        description=schedule.description,
        created_at=schedule.created_at.strftime("%Y-%m-%d %H:%M:%S")
    )

@router.put("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    data: ScheduleUpdate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新日程"""
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id, Schedule.user_id == user_id)
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="日程不存在")

    if data.title:
        schedule.title = data.title
    if data.scheduled_time:
        schedule.scheduled_time = datetime.strptime(data.scheduled_time, "%Y-%m-%dT%H:%M")
    if data.description is not None:
        schedule.description = data.description

    await db.commit()
    await db.refresh(schedule)

    return ScheduleResponse(
        id=schedule.id,
        title=schedule.title,
        scheduled_time=schedule.scheduled_time.strftime("%Y-%m-%d %H:%M"),
        description=schedule.description,
        created_at=schedule.created_at.strftime("%Y-%m-%d %H:%M:%S")
    )

@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除日程"""
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id, Schedule.user_id == user_id)
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="日程不存在")

    await db.delete(schedule)
    await db.commit()
    return {"success": True}


# ============================================
# 联系人相关
# ============================================

class ContactCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    birthday: Optional[str] = None
    remark: Optional[str] = None
    extra: Optional[str] = None

class ContactUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    birthday: Optional[str] = None
    remark: Optional[str] = None
    extra: Optional[str] = None

class ContactResponse(BaseModel):
    id: int
    name: str
    phone: Optional[str]
    birthday: Optional[str]
    remark: Optional[str]
    extra: Optional[str]
    created_at: str

@router.get("/contacts", response_model=List[ContactResponse])
async def list_contacts(
    keyword: Optional[str] = None,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取联系人列表"""
    query = select(Contact).where(Contact.user_id == user_id)

    if keyword:
        query = query.where(Contact.name.contains(keyword))

    query = query.order_by(Contact.name)
    result = await db.execute(query)
    contacts = result.scalars().all()

    return [
        ContactResponse(
            id=c.id,
            name=c.name,
            phone=c.phone,
            birthday=c.birthday,
            remark=c.remark,
            extra=c.extra,
            created_at=c.created_at if isinstance(c.created_at, str) else c.created_at.strftime("%Y-%m-%d %H:%M:%S")
        )
        for c in contacts
    ]

@router.post("/contacts", response_model=ContactResponse)
async def create_contact(
    data: ContactCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建联系人"""
    contact = Contact(
        user_id=user_id,
        name=data.name,
        phone=data.phone,
        birthday=data.birthday,
        remark=data.remark,
        extra=data.extra
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)

    return ContactResponse(
        id=contact.id,
        name=contact.name,
        phone=contact.phone,
        birthday=contact.birthday,
        remark=contact.remark,
        extra=contact.extra,
        created_at=contact.created_at if isinstance(contact.created_at, str) else contact.created_at.strftime("%Y-%m-%d %H:%M:%S")
    )

@router.put("/contacts/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: int,
    data: ContactUpdate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """更新联系人"""
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.user_id == user_id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")

    if data.name:
        contact.name = data.name
    if data.phone is not None:
        contact.phone = data.phone
    if data.birthday is not None:
        contact.birthday = data.birthday
    if data.remark is not None:
        contact.remark = data.remark
    if data.extra is not None:
        contact.extra = data.extra

    await db.commit()
    await db.refresh(contact)

    return ContactResponse(
        id=contact.id,
        name=contact.name,
        phone=contact.phone,
        birthday=contact.birthday,
        remark=contact.remark,
        extra=contact.extra,
        created_at=contact.created_at if isinstance(contact.created_at, str) else contact.created_at.strftime("%Y-%m-%d %H:%M:%S")
    )

@router.delete("/contacts/{contact_id}")
async def delete_contact(
    contact_id: int,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除联系人"""
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.user_id == user_id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="联系人不存在")

    await db.delete(contact)
    await db.commit()
    return {"success": True}


# ============================================
# 设置相关
# ============================================

# 临时存储用户设置
_temp_settings = {}  # user_id -> settings

class UserSettings(BaseModel):
    daily_reminder_enabled: bool = True
    daily_reminder_time: str = "08:00"
    pre_reminder_enabled: bool = True
    pre_reminder_minutes: int = 30
    birthday_reminder_enabled: bool = True
    birthday_reminder_days: int = 7

@router.get("/settings", response_model=UserSettings)
async def get_settings(user_id: str = Depends(get_current_user)):
    """获取用户设置"""
    settings = _temp_settings.get(user_id, UserSettings())
    return settings

@router.put("/settings", response_model=UserSettings)
async def update_settings(
    data: UserSettings,
    user_id: str = Depends(get_current_user)
):
    """更新用户设置"""
    _temp_settings[user_id] = data
    return data


# ============================================
# 订阅相关
# ============================================

class UserSubscription(BaseModel):
    module_id: str
    module_name: str
    enabled: bool

class ToggleSubscription(BaseModel):
    module_id: str
    enabled: bool

@router.get("/subscriptions", response_model=List[UserSubscription])
async def list_subscriptions(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户订阅状态"""
    # 获取所有模块
    from services.modules.registry import registry
    modules = registry.get_all()

    # 获取用户已订阅的模块
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscriptions = result.scalars().all()
    subscribed_ids = {s.module_id for s in subscriptions if s.enabled}

    return [
        UserSubscription(
            module_id=m.module_id,
            module_name=m.module_name,
            enabled=m.module_id in subscribed_ids
        )
        for m in modules
    ]

@router.post("/subscriptions/toggle")
async def toggle_subscription(
    data: ToggleSubscription,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """切换订阅状态"""
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.module_id == data.module_id
        )
    )
    subscription = result.scalar_one_or_none()

    if subscription:
        subscription.enabled = data.enabled
    else:
        subscription = Subscription(
            user_id=user_id,
            module_id=data.module_id,
            enabled=data.enabled
        )
        db.add(subscription)

    await db.commit()
    return {"success": True}
