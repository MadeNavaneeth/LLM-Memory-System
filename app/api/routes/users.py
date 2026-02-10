"""
User API Routes
"""
from typing import List
from fastapi import APIRouter, HTTPException

from app.database.models import UserCreate, UserResponse
from app.services.user_service import get_user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse)
async def create_user(user: UserCreate):
    """Create a new user"""
    service = get_user_service()
    
    # Check if username exists
    existing = service.get_user_by_username(user.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    return service.create_user(user)


@router.get("/", response_model=List[UserResponse])
async def get_all_users():
    """Get all users"""
    service = get_user_service()
    return service.get_all_users()


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get user by ID"""
    service = get_user_service()
    user = service.get_user(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.put("/{user_id}/preferences")
async def update_preferences(user_id: str, preferences_summary: str):
    """Update user preferences"""
    service = get_user_service()
    
    user = service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    service.update_preferences(user_id, preferences_summary)
    return {"message": "Preferences updated"}


@router.delete("/{user_id}")
async def delete_user(user_id: str):
    """Delete a user"""
    service = get_user_service()
    
    user = service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    service.delete_user(user_id)
    return {"message": "User deleted"}
