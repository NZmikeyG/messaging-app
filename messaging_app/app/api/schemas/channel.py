from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional
from datetime import datetime
from uuid import UUID


class ChannelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class ChannelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class ChannelMember(BaseModel):
    id: str
    email: str
    username: str

    @field_validator('id', mode='before')
    @classmethod
    def convert_id_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    model_config = ConfigDict(from_attributes=True)


class ChannelPublic(BaseModel):
    id: str
    name: str
    description: Optional[str]
    creator_id: str
    created_at: datetime
    members: List[ChannelMember]

    @field_validator('id', 'creator_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v

    model_config = ConfigDict(from_attributes=True)
