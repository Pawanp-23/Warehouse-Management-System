from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from commons.dependencies import get_actor_id, get_organization_id, require_roles
from core.apis.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UpdateUserRequest, UserResource
from core.controllers import auth_controller
from core.database import get_database

router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(payload: RegisterRequest):
    try: return await auth_controller.register(payload)
    except DuplicateKeyError as error: raise HTTPException(409, "Email is already registered") from error
    except PermissionError as error: raise HTTPException(403, str(error)) from error
    except ValueError as error: raise HTTPException(422, str(error)) from error


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest):
    try: return await auth_controller.login(str(payload.email), payload.password)
    except PermissionError as error: raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(error)) from error


@router.get("/me", response_model=UserResource)
async def me(actor_id: str = Depends(get_actor_id), organization_id: str = Depends(get_organization_id)):
    user = await get_database().users.find_one({"_id": actor_id, "organization_id": organization_id})
    if not user: raise HTTPException(404, "User not found")
    return auth_controller.resource(user)


@router.get("/users", response_model=list[UserResource], dependencies=[Depends(require_roles("admin"))])
async def users(organization_id: str = Depends(get_organization_id)):
    records = await get_database().users.find({"organization_id": organization_id}).sort("name", 1).to_list(length=500)
    return [auth_controller.resource(item) for item in records]


@router.patch("/users/{user_id}", response_model=UserResource, dependencies=[Depends(require_roles("admin"))])
async def update_user(user_id: str, payload: UpdateUserRequest, organization_id: str = Depends(get_organization_id)):
    changes = {key: value for key, value in payload.model_dump().items() if value is not None}
    changes["updated_at"] = datetime.now(timezone.utc)
    user = await get_database().users.find_one_and_update({"_id": user_id, "organization_id": organization_id}, {"$set": changes}, return_document=True)
    if not user: raise HTTPException(404, "User not found")
    return auth_controller.resource(user)


@router.delete("/users/{user_id}", status_code=204, dependencies=[Depends(require_roles("admin"))])
async def delete_user(user_id: str, organization_id: str = Depends(get_organization_id), actor_id: str = Depends(get_actor_id)):
    if user_id == actor_id: raise HTTPException(409, "Admin cannot delete their own active session")
    result = await get_database().users.delete_one({"_id": user_id, "organization_id": organization_id})
    if not result.deleted_count: raise HTTPException(404, "User not found")
