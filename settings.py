import os
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")
DEBUG = os.getenv('DEBUG').lower() == 'true'

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')
# used to encrypt insta access tokens
ENCRYPTION_KEY=os.getenv('ENCRYPTION_KEY')

REFRESH_TOKEN_EXPIRE_DAYS = 30
ACCESS_TOKEN_EXPIRE_HOURS = 24

JWT_ACCESS_SECRET =  os.getenv('JWT_ACCESS_SECRET')
JWT_REFRESH_SECRET = os.getenv('JWT_REFRESH_SECRET')

