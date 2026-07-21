"""Schema for the Users Trapper endpoint."""
from typing import Optional

from pydantic import BaseModel


class UserRecord(BaseModel):
    """Schema for ``/accounts/api/users`` items."""

    pk: int
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
