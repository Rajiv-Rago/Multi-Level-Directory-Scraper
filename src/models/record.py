"""Pydantic model for directory records."""

from datetime import datetime

from pydantic import BaseModel


class DirectoryRecord(BaseModel):
    region: str
    category: str
    name: str
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    description: str | None = None
    source_url: str
    scraped_at: datetime
