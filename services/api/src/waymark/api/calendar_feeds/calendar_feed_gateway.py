from sqlalchemy import select
from sqlalchemy.orm import Session

from waymark.models import CalendarFeed


class CalendarFeedGateway:
    """Raw persistence for per-user ICS calendar feed tokens."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, row: CalendarFeed) -> CalendarFeed:
        self._db.add(row)
        self._db.flush()
        return row

    def for_user(self, user_id: int) -> CalendarFeed | None:
        return self._db.scalar(
            select(CalendarFeed).where(CalendarFeed.user_id == user_id)
        )

    def by_token_hash(self, token_hash: str) -> CalendarFeed | None:
        return self._db.scalar(
            select(CalendarFeed).where(CalendarFeed.token_hash == token_hash)
        )

    def commit(self) -> None:
        self._db.commit()

    def refresh(self, row: CalendarFeed) -> None:
        self._db.refresh(row)
