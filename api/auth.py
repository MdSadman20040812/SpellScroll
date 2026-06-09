import jwt
from fastapi import Request, HTTPException, Depends
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

async def get_current_user(request: Request):
    """
    FastAPI dependency that decodes a JWT token from Cookie or Auth header,
    returning the authenticated Django User object.
    """
    token = request.cookies.get('access_token')
    if not token:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
    if not token:
        raise HTTPException(status_code=401, detail="Authentication credentials not provided")
        
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get('user_id')
        user = User.objects.get(id=user_id)
        return user
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token or signature")
    except User.DoesNotExist:
        raise HTTPException(status_code=401, detail="User not found")
        
async def get_current_admin(user = Depends(get_current_user)):
    """
    Verifies that the logged-in user is an administrator.
    """
    if not (user.is_superuser or getattr(user, 'is_admin_user', False)):
        raise HTTPException(status_code=403, detail="Admin permissions required")
    return user
