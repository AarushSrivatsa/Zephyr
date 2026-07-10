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
	scheduled_posts = Relationship('ScheduledPostModel', back_populates='user')

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

class PostType(enum.Enum):
    image = "image"
    reel = "reel"
    carousel = "carousel"

class PostStatus(enum.Enum):
    pending = "pending"
    published = "published"
    failed = "failed"

class ScheduledPostModel(Base):
	__tablename__ = 'scheduled_posts'
	id : Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	caption : Mapped[Optional[str]] = mapped_column(Text,nullable=True)
	post_type : Mapped[PostType] = mapped_column(Enum(PostType),nullable=False)
	status : Mapped[PostStatus] = mapped_column(Enum(PostStatus), server_default='pending')
	scheduled_at : Mapped[datetime] = mapped_column(DateTime(timezone=True),nullable=False)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
	error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Foreign Keys
	user_id: Mapped[str] = mapped_column(String(50), ForeignKey('users.user_id', ondelete='CASCADE'), index=True)

    # Relationships
	user = Relationship('UserModel', back_populates='scheduled_posts')
	media_items = Relationship('ScheduledPostMediaModel', back_populates='post')

class ScheduledPostMediaModel(Base):
    __tablename__ = 'scheduled_post_media'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    media_url: Mapped[str] = mapped_column(Text, nullable=False)
    media_type: Mapped[str] = mapped_column(String(20), nullable=False)  # IMAGE, VIDEO, REELS
    order: Mapped[int] = mapped_column(Integer, default=0)

    # Foreign Keys
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey('scheduled_posts.id', ondelete='CASCADE'), index=True)

    # Relationships
    post = Relationship('ScheduledPostModel', back_populates='media_items')

