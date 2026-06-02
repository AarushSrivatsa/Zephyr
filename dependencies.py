from database.initialization import AsyncSessionLocal
from httpx import AsyncClient

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

async def get_http_client():
    async with AsyncClient() as client:
        yield client
