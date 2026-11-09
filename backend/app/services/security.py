import hashlib
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
import base64
from ..config import settings

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(p: str) -> str: return pwd_ctx.hash(p)
def verify_password(p: str, h: str) -> bool: return pwd_ctx.verify(p, h)

def create_access_token(sub: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_min)
    return jwt.encode({"sub": sub, "exp": exp}, settings.secret_key, algorithm=settings.jwt_algorithm)

def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        sub = payload.get("sub")
        if not sub: raise JWTError("no sub")
        return sub
    except JWTError as e:
        raise ValueError("invalid token") from e

def _fernet() -> Fernet:
    key = settings.encryption_key
    if not key:
        digest = hashlib.sha256(settings.secret_key.encode()).digest()
        key = base64.urlsafe_b64encode(digest).decode()
    return Fernet(key.encode())

def encrypt_secret(plaintext: str) -> str: return _fernet().encrypt(plaintext.encode()).decode()
def decrypt_secret(ciphertext: str) -> str: return _fernet().decrypt(ciphertext.encode()).decode()
