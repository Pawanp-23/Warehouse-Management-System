from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, use_enum_values=True, extra="forbid", str_strip_whitespace=True)


class CreatedResource(APIModel):
    id: str
    created_at: datetime


class CommandResponse(APIModel):
    id: str
    status: str


class Pagination(APIModel):
    limit: int = Field(default=50, ge=1, le=100)
