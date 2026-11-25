from fastapi import APIRouter, Request, Response

from waymark.api.calendar_feeds.calendar_feed_service import CalendarFeedService
from waymark.api.calendar_feeds.calendar_ics_builder import FeedMode
from waymark.db import DbSession


class PublicCalendarFeedApi:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/api/public/calendar", tags=["public-calendar-feed"])
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route(
            "/{token}.ics",
            self.get_ics,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/{token}/redacted.ics",
            self.get_redacted_ics,
            methods=["GET"],
        )

    def get_ics(self, token: str, request: Request, db: DbSession) -> Response:
        return self._ics_response(token, request, db, mode="full", filename="waymark.ics")

    def get_redacted_ics(self, token: str, request: Request, db: DbSession) -> Response:
        return self._ics_response(
            token, request, db, mode="redacted", filename="waymark-redacted.ics"
        )

    def _ics_response(
        self,
        token: str,
        request: Request,
        db: DbSession,
        *,
        mode: FeedMode,
        filename: str,
    ) -> Response:
        origin = f"{request.url.scheme}://{request.url.netloc}"
        body = CalendarFeedService(db).render_ics(token, app_origin=origin, mode=mode)
        return Response(
            content=body,
            media_type="text/calendar; charset=utf-8",
            headers={
                "Cache-Control": "private, no-store",
                "Content-Disposition": f'inline; filename="{filename}"',
            },
        )


public_calendar_feed_api = PublicCalendarFeedApi()
