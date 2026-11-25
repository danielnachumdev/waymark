from datetime import UTC, date, datetime
from typing import Literal

from icalendar import Calendar, Event

from waymark.models import Task

_SHARED_PREFIX = "[Shared] "
FeedMode = Literal["full", "redacted"]


class CalendarIcsBuilder:
    """Build RFC 5545 calendar bytes from dated open tasks."""

    def build(
        self,
        tasks: list[Task],
        *,
        feed_owner_user_id: int,
        app_origin: str,
        mode: FeedMode = "full",
    ) -> bytes:
        cal = Calendar()
        cal.add("prodid", "-//Waymark//Calendar Feed//EN")
        cal.add("version", "2.0")
        cal.add("calscale", "GREGORIAN")
        cal.add("method", "PUBLISH")
        cal.add(
            "x-wr-calname",
            "Waymark" if mode == "full" else "Waymark (redacted)",
        )
        origin = app_origin.rstrip("/")
        for task in tasks:
            cal.add_component(
                self._event(
                    task,
                    feed_owner_user_id=feed_owner_user_id,
                    origin=origin,
                    mode=mode,
                )
            )
        return cal.to_ical()

    def _event(
        self,
        task: Task,
        *,
        feed_owner_user_id: int,
        origin: str,
        mode: FeedMode,
    ) -> Event:
        due = self._due_date(task.due_at)
        event = Event()
        event.add("uid", f"{task.public_id}@waymark")
        event.add("dtstamp", datetime.now(UTC))
        event.add("dtstart", due)
        event.add("summary", self._summary(task, feed_owner_user_id, mode))
        event.add("transp", "TRANSPARENT")
        if mode == "full":
            url = f"{origin}/tasks/{task.public_id}"
            event.add("url", url)
            notes = task.description.strip() if task.description else ""
            event.add("description", f"{notes}\n\n{url}".strip() if notes else url)
        return event

    @staticmethod
    def _summary(task: Task, feed_owner_user_id: int, mode: FeedMode) -> str:
        shared = task.owner_user_id != feed_owner_user_id
        if mode == "redacted":
            label = "Waymark task"
            return f"{_SHARED_PREFIX}{label}" if shared else label
        if shared:
            return f"{_SHARED_PREFIX}{task.title}"
        return task.title

    @staticmethod
    def _due_date(due_at: datetime | None) -> date:
        assert due_at is not None
        if due_at.tzinfo is None:
            due_at = due_at.replace(tzinfo=UTC)
        return due_at.astimezone(UTC).date()
