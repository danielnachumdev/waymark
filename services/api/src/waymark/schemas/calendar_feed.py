from datetime import datetime

from pydantic import BaseModel


class CalendarFeedOut(BaseModel):
    active: bool
    created_at: datetime | None = None
    last_accessed_at: datetime | None = None
    revoked_at: datetime | None = None


class CalendarFeedTokenOut(CalendarFeedOut):
    token: str
