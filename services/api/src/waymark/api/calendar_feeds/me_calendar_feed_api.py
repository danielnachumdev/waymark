from fastapi import APIRouter

from waymark.api.calendar_feeds.calendar_feed_service import CalendarFeedService
from waymark.auth import AuthenticatedPrincipal
from waymark.db import DbSession
from waymark.schemas.calendar_feed import CalendarFeedOut, CalendarFeedTokenOut


class MeCalendarFeedApi:
    def __init__(self) -> None:
        self.router = APIRouter(prefix="/api/me/calendar-feed", tags=["calendar-feed"])
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route(
            "",
            self.get_status,
            methods=["GET"],
            response_model=CalendarFeedOut,
        )
        self.router.add_api_route(
            "",
            self.create,
            methods=["POST"],
            response_model=CalendarFeedTokenOut,
            status_code=201,
        )
        self.router.add_api_route(
            "/rotate",
            self.rotate,
            methods=["POST"],
            response_model=CalendarFeedTokenOut,
        )
        self.router.add_api_route(
            "/revoke",
            self.revoke,
            methods=["POST"],
            response_model=CalendarFeedOut,
        )

    def get_status(
        self, db: DbSession, principal: AuthenticatedPrincipal
    ) -> CalendarFeedOut:
        return CalendarFeedService(db).get_status(principal)

    def create(
        self, db: DbSession, principal: AuthenticatedPrincipal
    ) -> CalendarFeedTokenOut:
        return CalendarFeedService(db).create(principal)

    def rotate(
        self, db: DbSession, principal: AuthenticatedPrincipal
    ) -> CalendarFeedTokenOut:
        return CalendarFeedService(db).rotate(principal)

    def revoke(
        self, db: DbSession, principal: AuthenticatedPrincipal
    ) -> CalendarFeedOut:
        return CalendarFeedService(db).revoke(principal)


me_calendar_feed_api = MeCalendarFeedApi()
