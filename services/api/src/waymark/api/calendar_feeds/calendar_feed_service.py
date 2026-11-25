import secrets
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from waymark.api.calendar_feeds.calendar_feed_gateway import CalendarFeedGateway
from waymark.api.calendar_feeds.calendar_ics_builder import CalendarIcsBuilder, FeedMode
from waymark.api.tasks.task_gateway import TaskGateway
from waymark.auth.principal import Principal
from waymark.auth.task_access_service import TaskAccessService
from waymark.models import CalendarFeed
from waymark.schemas.calendar_feed import CalendarFeedOut, CalendarFeedTokenOut
from waymark.security import api_token_hasher

TOKEN_PREFIX = "wcf_"


class CalendarFeedService:
    """Mint, rotate, revoke, and render a user's ICS calendar subscription."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._gateway = CalendarFeedGateway(db)
        self._tasks = TaskGateway(db)
        self._access = TaskAccessService(db)
        self._ics = CalendarIcsBuilder()

    def get_status(self, principal: Principal) -> CalendarFeedOut:
        row = self._gateway.for_user(principal.user_id)
        return self._out(row)

    def create(self, principal: Principal) -> CalendarFeedTokenOut:
        row = self._gateway.for_user(principal.user_id)
        if row is not None and row.revoked_at is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Calendar feed already exists; rotate or revoke it first",
            )
        raw = self._mint_raw_token()
        if row is None:
            row = CalendarFeed(
                user_id=principal.user_id,
                token_hash=api_token_hasher.hash(raw),
            )
            self._gateway.add(row)
        else:
            row.token_hash = api_token_hasher.hash(raw)
            row.revoked_at = None
            row.last_accessed_at = None
            row.created_at = datetime.now(UTC)
        self._gateway.commit()
        self._gateway.refresh(row)
        return CalendarFeedTokenOut(**self._out(row).model_dump(), token=raw)

    def rotate(self, principal: Principal) -> CalendarFeedTokenOut:
        row = self._require_active(principal.user_id)
        raw = self._mint_raw_token()
        row.token_hash = api_token_hasher.hash(raw)
        self._gateway.commit()
        self._gateway.refresh(row)
        return CalendarFeedTokenOut(**self._out(row).model_dump(), token=raw)

    def revoke(self, principal: Principal) -> CalendarFeedOut:
        row = self._require_active(principal.user_id)
        row.revoked_at = datetime.now(UTC)
        self._gateway.commit()
        self._gateway.refresh(row)
        return self._out(row)

    def render_ics(
        self,
        raw_token: str,
        *,
        app_origin: str,
        mode: FeedMode = "full",
    ) -> bytes:
        row = self._require_active_by_token(raw_token)
        row.last_accessed_at = datetime.now(UTC)
        self._gateway.commit()
        accessible = self._access.accessible_task_ids_select(row.user_id)
        tasks = self._tasks.list_open_dated(accessible)
        return self._ics.build(
            tasks,
            feed_owner_user_id=row.user_id,
            app_origin=app_origin,
            mode=mode,
        )

    def _require_active(self, user_id: int) -> CalendarFeed:
        row = self._gateway.for_user(user_id)
        if row is None or row.revoked_at is not None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Calendar feed not found")
        return row

    def _require_active_by_token(self, raw_token: str) -> CalendarFeed:
        row = self._gateway.by_token_hash(api_token_hasher.hash(raw_token))
        if row is None or row.revoked_at is not None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Calendar feed not found")
        return row

    @staticmethod
    def _mint_raw_token() -> str:
        return f"{TOKEN_PREFIX}{secrets.token_urlsafe(32)}"

    @staticmethod
    def _out(row: CalendarFeed | None) -> CalendarFeedOut:
        if row is None:
            return CalendarFeedOut(active=False)
        return CalendarFeedOut(
            active=row.revoked_at is None,
            created_at=row.created_at,
            last_accessed_at=row.last_accessed_at,
            revoked_at=row.revoked_at,
        )
