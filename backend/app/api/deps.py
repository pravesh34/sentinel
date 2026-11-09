from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from ..database.session import get_db
from ..models.entities import User
from ..services.security import decode_token

bearer = HTTPBearer(auto_error=False)

def get_current_user(request: Request, creds: HTTPAuthorizationCredentials | None = Depends(bearer),
                     db: Session = Depends(get_db)) -> User:
    # Allow header-less in test mode via X-Test-User? No — require JWT strictly.
    if not creds:
        raise HTTPException(status_code=401, detail="missing token")
    try:
        user_id = decode_token(creds.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="invalid token")
    user = db.query(User).filter_by(id=user_id).first()
    if not user: raise HTTPException(status_code=404, detail="user not found")
    return user
