from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional, List
from enum import Enum
from datetime import datetime
import re

class UserRole(str, Enum):
    ADMIN = "Admin"
    EDITOR = "Editor"
    CONTRIBUTOR = "Contributor"
    SEARCHER = "Searcher"
    VIEWER = "Viewer"

class UserIn(BaseModel):
    uuid: Optional[str] = None
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    name: str
    disabled: Optional[bool] = False
    password: str = Field(..., min_length=6)
    datecreated: Optional[datetime] = None

    @field_validator('username')
    @classmethod
    def username_must_be_valid(cls, v):
        # Define a regex pattern that allows letters, numbers, underscores, dots, @, and hyphens
        pattern = re.compile(r'^[A-Za-z0-9_.@-]+$')
        if not pattern.match(v):
            raise ValueError('Username must contain only letters, numbers, underscores, dots, @, or hyphens')
        return v

    model_config = ConfigDict(from_attributes=True)

    def to_dict(self):
        return self.model_dump()

class User(BaseModel):
    uuid: str
    username: str
    email: EmailStr
    name: str
    disabled: Optional[bool] = False
    datecreated: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    def to_dict(self):
        return self.model_dump()

class UserRoles(BaseModel):
    username: str
    roles: List[UserRole]

    @field_validator('roles')
    @classmethod
    def roles_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('At least one role must be assigned')
        return v

    # Removed json_schema_extra as Pydantic handles Enums automatically
    model_config = ConfigDict()

    def to_dict(self):
        return self.model_dump()
