"""Schema for the Users Trapper endpoint."""
from typing import Optional

from pydantic import BaseModel
from trapper_client._deprecated import deprecated_getattr


class User(BaseModel):
    """Schema for ``/accounts/api/users`` items."""

    pk: int
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None


__getattr__ = deprecated_getattr(__name__)
