from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from settings import DATABASE_URL, DEBUG

engine = create_async_engine(
	url=DATABASE_URL,
	pool_size=10,
	max_overflow=20,
	pool_timeout=30, 
	echo=DEBUG,
	pool_pre_ping=True,
	pool_recycle=1800,
	connect_args={"ssl": "require"})

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
	def __repr__(self):
          cols = {c.name: getattr(self, c.name) for c in self.__table__.columns}
          return f"{self.__class__.__name__}({cols})\n"

async def get_db():
     async with AsyncSessionLocal() as session:    
        try:
             yield session          
             await session.commit()		      
        except Exception:
             await session.rollback()     
             raise               
        finally:
             await session.close()  