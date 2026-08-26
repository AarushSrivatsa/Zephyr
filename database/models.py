from database.initialization import Base
from sqlalchemy.orm import Mapped, mapped_column, Relationship
from sqlalchemy import String, DateTime, func, Text, ForeignKey, UniqueConstraint, Integer, Boolean
from datetime import datetime, timezone, timedelta
from sqlalchemy.dialects.postgresql import ARRAY
from typing import Optional
import enum

class UserModel(Base):
    __tablename__ = 'users'

    user_id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50))
    profile_pic_url: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

    # nullable so delete_account can clear it before the 15-day purge
    encrypted_instagram_access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    instagram_token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    subscription = Relationship('SubscriptionModel', back_populates='user', uselist=False)
    rules = Relationship('RuleModel', back_populates='user')
    refresh_tokens = Relationship('RefreshTokenModel', back_populates='user')

class SubscriptionModel(Base):
    __tablename__ = 'subscriptions'

    user_id: Mapped[str] = mapped_column(String(50), ForeignKey('users.user_id', ondelete='CASCADE'), index=True, primary_key=True)
    next_billing_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc) + timedelta(days=7))

    user = Relationship('UserModel', back_populates='subscription', passive_deletes=True)

class RuleModel(Base):
    __tablename__ = 'rules'

    __table_args__ = (
        UniqueConstraint("media_id", "catchphrase"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    link: Mapped[str] = mapped_column(String(100), nullable=False)
    media_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    catchphrase: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    dm_message: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    reply_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    count: Mapped[int] = mapped_column(Integer, server_default='0')
    is_case_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)

    user_id: Mapped[str] = mapped_column(String(50), ForeignKey('users.user_id', ondelete='CASCADE'), index=True)

    user = Relationship('UserModel', back_populates='rules')
    dms = Relationship('DMLogsModel', back_populates='rule')

class DMLogsModel(Base):
    __tablename__ = 'dm_logs'

    __table_args__ = (
        UniqueConstraint("commenter_ig_id", "rule_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    commenter_ig_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    media_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    comment_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    rule_id: Mapped[int] = mapped_column(Integer, ForeignKey('rules.id', ondelete='CASCADE'), index=True)

    rule = Relationship('RuleModel', back_populates='dms')

class RefreshTokenModel(Base):
    __tablename__ = 'refresh_tokens'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user_id: Mapped[str] = mapped_column(String(50), ForeignKey('users.user_id', ondelete='CASCADE'), index=True)

    user = Relationship('UserModel', back_populates='refresh_tokens')