from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database.initialization import get_db
from database.models import RuleModel, UserModel
from utils.tokens import get_current_user
from pydantic import BaseModel
from utils.media_id_extraction import extract_media_id
from datetime import datetime
from sqlalchemy import select

router = APIRouter(prefix='/rules', tags=['Rules'])

class RuleCreate(BaseModel):
    link: str
    catchphrase: str
    dm_message: str
    reply_message: str | None = None
    

class RuleResponse(BaseModel):
    id: int
    link: str
    media_id: str
    catchphrase: str
    dm_message: str
    reply_message: str | None
    is_active: bool
    count: int
    created_at: datetime

    class Config:
        from_attributes = True

@router.post('',response_model=RuleResponse)
async def create_rule(rule: RuleCreate, db: AsyncSession = Depends(get_db), user: UserModel = Depends(get_current_user)):
    
    media_info = await extract_media_id(url=rule.link, user=user)
    
    new_rule = RuleModel(
        link=media_info['permalink'],
        media_id=media_info['media_id'],
        catchphrase=rule.catchphrase,
        dm_message=rule.dm_message,
        reply_message=rule.reply_message,
        user_id=user.user_id)
    
    db.add(new_rule)
    
    return new_rule

@router.get('',response_model=list[RuleResponse])
async def list_rules(db: AsyncSession = Depends(get_db), user: UserModel = Depends(get_current_user)):
    result = await db.execute(select(RuleModel).where(RuleModel.user_id == user.user_id))
    rules = result.scalars().all()
    return rules

@router.get('/{rule_id}',response_model=RuleResponse)
async def get_rule(rule_id: int, db: AsyncSession = Depends(get_db), user: UserModel = Depends(get_current_user)):
    result = await db.execute(select(RuleModel).where(RuleModel.id == rule_id, RuleModel.user_id == user.user_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail='Rule not found')
    return rule

class RuleUpdate(BaseModel):
    link: str | None = None
    catchphrase: str | None = None
    dm_message: str | None = None
    reply_message: str | None = None
    is_active: bool | None = None

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

    return rule

@router.delete('/{rule_id}')
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db), user: UserModel = Depends(get_current_user)):
    result = await db.execute(select(RuleModel).where(RuleModel.id == rule_id, RuleModel.user_id == user.user_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail='Rule not found')

    await db.delete(rule)
    return {'message': 'Rule deleted successfully'}