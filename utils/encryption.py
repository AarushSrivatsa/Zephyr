# utils/encryption.py
from cryptography.fernet import Fernet
from settings import ENCRYPTION_KEY

fernet = Fernet(ENCRYPTION_KEY)

def encrypt(token: str) -> str:
    return fernet.encrypt(token.encode()).decode()

def decrypt(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()
