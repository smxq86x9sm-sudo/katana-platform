from fastapi import Header, HTTPException, status
from .config import settings

async def verify_api_token(x_api_token: str = Header(None, alias="X-API-Token")):
    if not x_api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-API-Token header")
    if x_api_token != settings.API_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API Token")
