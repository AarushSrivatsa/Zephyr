from database.initialization import Base
from sqlalchemy.orm import Mapped, mapped_column, Relationship
from sqlalchemy import String, DateTime, func, Text, ForeignKey, UniqueConstraint, Integer, Boolean
from datetime import datetime, timezone, timedelta
from sqlalchemy import Enum
from typing import Optional
import enum

class UserModel(Base):
	__tablename__ = 'users'

	# individual columns
	user_id : Mapped[str] = mapped_column(String(50),primary_key=True, index=True)
	username : Mapped[str] = mapped_column(String(50))
	profile_pic_url : Mapped[str] = mapped_column(Text)
	created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default= func.now())
	deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

	#instagram columns
	encrypted_instagram_access_token : Mapped[str] = mapped_column(Text)
	instagram_token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

	# relationships
	subscription = Relationship('SubscriptionModel',back_populates='user',uselist=False)
	rules = Relationship('RuleModel',back_populates='user')
	refresh_tokens = Relationship('RefreshTokenModel',back_populates='user')

class SubscriptionModel(Base):
	__tablename__ = 'subscriptions'
	
	# primary key
	user_id : Mapped[str] = mapped_column(String(50),ForeignKey('users.user_id',ondelete='CASCADE'),index=True,primary_key=True)

	next_billing_date : Mapped[datetime] = mapped_column(DateTime(timezone=True),default= lambda : datetime.now(timezone.utc) + timedelta(days=7))

	#relationships
	user = Relationship('UserModel',back_populates='subscription',passive_deletes=True)

class RuleModel(Base):
	__tablename__ = 'rules'

	__table_args__ = (
   	UniqueConstraint("media_id", "catchphrase"),
	)
	
	id : Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True)

	link : Mapped[str] = mapped_column(String(100),nullable=False)
	media_id: Mapped[str] = mapped_column(String(100),nullable=False,index=True)
	catchphrase: Mapped[str] = mapped_column(String(100),nullable=False,index=True)
	dm_message: Mapped[str] = mapped_column(Text,nullable=False)
	reply_message: Mapped[Optional[str]] = mapped_column(Text,nullable=True,default=None)

	is_active: Mapped[bool] = mapped_column(Boolean,default=True)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())
	count : Mapped[int] = mapped_column(Integer, server_default='0')

	# Foreign Keys
	user_id : Mapped[str] = mapped_column(String(50), ForeignKey('users.user_id',ondelete='CASCADE'),index=True)

	# Relationships
	user = Relationship('UserModel',back_populates='rules')
	dms = Relationship('DMLogsModel',back_populates='rule')

class DMLogsModel(Base):
	__tablename__ = 'dm_logs'

	__table_args__ = (
    	UniqueConstraint("commenter_ig_id", "rule_id"),
	)
	
	id: Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True)
	commenter_ig_id: Mapped[str] = mapped_column(String(100),nullable=False,index=True)
	media_id: Mapped[str] = mapped_column(String(100),nullable=False,index=True)
	comment_id: Mapped[str] = mapped_column(String(100),nullable=False,unique=True,index=True)
	sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),server_default=func.now())

	#Foreign Keys
	rule_id : Mapped[int] = mapped_column(Integer, ForeignKey('rules.id',ondelete='CASCADE'),index=True)

	#Relationships
	rule = Relationship('RuleModel',back_populates='dms')

class RefreshTokenModel(Base):
    __tablename__ = 'refresh_tokens'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Foreign Keys
    user_id: Mapped[str] = mapped_column(String(50), ForeignKey('users.user_id', ondelete='CASCADE'), index=True)

    # Relationships
    user = Relationship('UserModel', back_populates='refresh_tokens')