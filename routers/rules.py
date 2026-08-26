from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database.initialization import get_db
from database.models import RuleModel, UserModel
from utils.token_handling import get_current_user
from pydantic import BaseModel, field_validator
from utils.media_id_extraction import extract_media_id
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix='/rules', tags=['Rules'])

class RuleCreate(BaseModel):
    link: str
    catchphrase: str
    dm_message: list[str]
    reply_message: str | None = None
    is_case_sensitive: bool = False

    @field_validator('catchphrase')
    @classmethod
    def normalize_catchphrase(cls, v: str) -> str:
        # NOTE: no .lower() here — original case must be preserved so
        # case-sensitive rules have something meaningful to compare against.
        return v.strip()

    @field_validator('dm_message', mode='before')
    @classmethod
    def coerce_dm_message(cls, v):
        if isinstance(v, str):
            return [v]
        return v

    @field_validator('dm_message')
    @classmethod
    def dm_message_not_empty(cls, v: list[str]) -> list[str]:
        cleaned = [m.strip() for m in v if m and m.strip()]
        if not cleaned:
            raise ValueError('dm_message must contain at least one non-empty message')
        return cleaned

class RuleResponse(BaseModel):
    id: int
    link: str
    catchphrase: str
    dm_message: list[str]
    reply_message: str | None
    is_active: bool
    is_case_sensitive: bool
    count: int
    created_at: datetime

    class Config:
        from_attributes = True


@router.post('', response_model=RuleResponse)
async def create_rule(rule: RuleCreate, db: AsyncSession = Depends(get_db), user: UserModel = Depends(get_current_user)):
    media_info = await extract_media_id(url=rule.link, user=user)

    new_rule = RuleModel(
        link=media_info['permalink'],
        media_id=media_info['media_id'],
        catchphrase=rule.catchphrase,
        dm_message=rule.dm_message,
        reply_message=rule.reply_message,
        is_case_sensitive=rule.is_case_sensitive,
        user_id=user.user_id
    )

    db.add(new_rule)
    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail='A rule with this catchphrase already exists for that post')
    await db.refresh(new_rule)
    return new_rule

@router.get('', response_model=list[RuleResponse])
async def list_rules(page: int = 1, limit: int = 10, db: AsyncSession = Depends(get_db), user: UserModel = Depends(get_current_user)):
    offset = (page - 1) * limit
    result = await db.execute(
        select(RuleModel)
        .where(RuleModel.user_id == user.user_id)
        .offset(offset)
        .limit(limit)
    )
    return result.scalars().all()

@router.get('/{rule_id}', response_model=RuleResponse)
async def get_rule(rule_id: int, db: AsyncSession = Depends(get_db), user: UserModel = Depends(get_current_user)):
    result = await db.execute(select(RuleModel).where(RuleModel.id == rule_id, RuleModel.user_id == user.user_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail='Rule not found')
    return rule

class RuleUpdate(BaseModel):
    link: str | None = None
    catchphrase: str | None = None
    dm_message: list[str] | None = None
    reply_message: str | None = None
    is_active: bool | None = None
    is_case_sensitive: bool | None = None

    @field_validator('catchphrase')
    @classmethod
    def normalize_catchphrase(cls, v: str | None) -> str | None:
        if v is not None:
            return v.strip()
        return v

    @field_validator('dm_message', mode='before')
    @classmethod
    def coerce_dm_message(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            return [v]
        return v

    @field_validator('dm_message')
    @classmethod
    def dm_message_not_empty(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        cleaned = [m.strip() for m in v if m and m.strip()]
        if not cleaned:
            raise ValueError('dm_message must contain at least one non-empty message')
        return cleaned

@router.patch('/{rule_id}', response_model=RuleResponse)
async def update_rule(rule_id: int, rule_update: RuleUpdate, db: AsyncSession = Depends(get_db), user: UserModel = Depends(get_current_user)):
    result = await db.execute(select(RuleModel).where(RuleModel.id == rule_id, RuleModel.user_id == user.user_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail='Rule not found')

    update_data = rule_update.model_dump(exclude_unset=True)

    if 'link' in update_data:
        media_info = await extract_media_id(url=update_data['link'], user=user)
        update_data['link'] = media_info['permalink']
        update_data['media_id'] = media_info['media_id']

    for field, value in update_data.items():
        setattr(rule, field, value)

    try:
        await db.flush()
    except IntegrityError:
        raise HTTPException(status_code=409, detail='A rule with this catchphrase already exists for that post')

    await db.refresh(rule)
    return rule

@router.delete('/{rule_id}')
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db), user: UserModel = Depends(get_current_user)):
    result = await db.execute(select(RuleModel).where(RuleModel.id == rule_id, RuleModel.user_id == user.user_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail='Rule not found')

    await db.delete(rule)
    return {'message': 'Rule deleted successfully'}