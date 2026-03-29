from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class TimelineEvent:
    id: str
    title: str
    book: str
    chapter_start: int
    verse_start: int
    chapter_end: int
    verse_end: int
    approx_start_year: int | None
    approx_end_year: int | None
    time_label: str
    location_name: str
    latitude: float | None
    longitude: float | None
    event_type: str
    people: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    summary: str = ""
    sources: list[str] = field(default_factory=list)
    confidence: float = 0.0

    @property
    def reference(self) -> str:
        start = f"{self.book} {self.chapter_start}:{self.verse_start}"
        end = f"{self.chapter_end}:{self.verse_end}"
        if (self.chapter_start, self.verse_start) == (self.chapter_end, self.verse_end):
            return start
        return f"{start}-{end}"

    @property
    def year_sort_key(self) -> int:
        return self.approx_start_year if self.approx_start_year is not None else 10**9

    @property
    def has_coordinates(self) -> bool:
        return self.latitude is not None and self.longitude is not None


def _split_pipe(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split("|") if part.strip()]


def _parse_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _parse_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


class BibleTimelineEngine:
    ERA_ORDER = [
        "Primeval",
        "Patriarchs",
        "Exodus/Wilderness",
        "Conquest/Judges",
        "United Kingdom",
        "Divided Kingdom",
        "Exile/Return",
        "Second Temple",
        "Life of Christ",
        "Acts/Apostolic",
    ]

    def __init__(self, csv_path: str | Path):
        self.csv_path = Path(csv_path)
        self._events: list[TimelineEvent] = []
        self.load_events()

    def load_events(self) -> None:
        self._events.clear()
        with self.csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self._events.append(
                    TimelineEvent(
                        id=row["id"].strip(),
                        title=row["title"].strip(),
                        book=row["book"].strip(),
                        chapter_start=int(row["chapter_start"]),
                        verse_start=int(row["verse_start"]),
                        chapter_end=int(row["chapter_end"]),
                        verse_end=int(row["verse_end"]),
                        approx_start_year=_parse_int(row.get("approx_start_year")),
                        approx_end_year=_parse_int(row.get("approx_end_year")),
                        time_label=(row.get("time_label") or "").strip(),
                        location_name=(row.get("location_name") or "").strip(),
                        latitude=_parse_float(row.get("latitude")),
                        longitude=_parse_float(row.get("longitude")),
                        event_type=(row.get("event_type") or "").strip(),
                        people=_split_pipe(row.get("people")),
                        tags=_split_pipe(row.get("tags")),
                        summary=(row.get("summary") or "").strip(),
                        sources=_split_pipe(row.get("sources")),
                        confidence=float(row.get("confidence") or 0.0),
                    )
                )

    def get_all_events(self) -> list[TimelineEvent]:
        return sorted(self._events, key=lambda e: (e.year_sort_key, e.book, e.chapter_start, e.verse_start))

    def search_events(self, query: str) -> list[TimelineEvent]:
        q = query.strip().lower()
        if not q:
            return self.get_all_events()
        results = []
        for event in self._events:
            haystack = " ".join([
                event.title,
                event.book,
                event.location_name,
                event.event_type,
                event.summary,
                " ".join(event.people),
                " ".join(event.tags),
                " ".join(event.sources),
                self.get_event_era(event),
            ]).lower()
            if q in haystack:
                results.append(event)
        return sorted(results, key=lambda e: (e.year_sort_key, e.title))

    def get_events_for_book(self, book: str) -> list[TimelineEvent]:
        target = book.strip().lower()
        return [e for e in self.get_all_events() if e.book.lower() == target]

    def get_events_for_person(self, person: str) -> list[TimelineEvent]:
        target = person.strip().lower()
        return [e for e in self.get_all_events() if any(p.lower() == target for p in e.people)]

    def get_events_for_location(self, location: str) -> list[TimelineEvent]:
        target = location.strip().lower()
        return [e for e in self.get_all_events() if e.location_name.lower() == target]

    def get_events_for_tag(self, tag: str) -> list[TimelineEvent]:
        target = tag.strip().lower()
        return [e for e in self.get_all_events() if any(t.lower() == target for t in e.tags)]

    def filter_events(self, *, book: str | None = None, person: str | None = None, location: str | None = None, tag: str | None = None, event_type: str | None = None, has_coordinates: bool | None = None) -> list[TimelineEvent]:
        events: Iterable[TimelineEvent] = self._events
        if book:
            b = book.strip().lower()
            events = [e for e in events if e.book.lower() == b]
        if person:
            p = person.strip().lower()
            events = [e for e in events if any(x.lower() == p for x in e.people)]
        if location:
            loc = location.strip().lower()
            events = [e for e in events if e.location_name.lower() == loc]
        if tag:
            t = tag.strip().lower()
            events = [e for e in events if any(x.lower() == t for x in e.tags)]
        if event_type:
            et = event_type.strip().lower()
            events = [e for e in events if e.event_type.lower() == et]
        if has_coordinates is not None:
            events = [e for e in events if e.has_coordinates is has_coordinates]
        return sorted(list(events), key=lambda e: (e.year_sort_key, e.title))

    def get_event_era(self, event: TimelineEvent) -> str:
        year = event.approx_start_year
        title = event.title.lower()
        book = event.book.lower()
        if year is None:
            if book in {"matthew", "mark", "luke", "john"} or "jesus" in title:
                return "Life of Christ"
            if book == "acts":
                return "Acts/Apostolic"
            return "Second Temple"
        if year <= -2200:
            return "Primeval"
        if year <= -1700:
            return "Patriarchs"
        if year <= -1400:
            return "Exodus/Wilderness"
        if year <= -1050:
            return "Conquest/Judges"
        if year <= -930:
            return "United Kingdom"
        if year <= -586:
            return "Divided Kingdom"
        if year <= -400:
            return "Exile/Return"
        if year < 1:
            return "Second Temple"
        if year <= 33:
            return "Life of Christ"
        return "Acts/Apostolic"

    def get_eras(self) -> dict[str, list[TimelineEvent]]:
        buckets = {era: [] for era in self.ERA_ORDER}
        for event in self.get_all_events():
            buckets[self.get_event_era(event)].append(event)
        return buckets

    def get_events_for_era(self, era: str) -> list[TimelineEvent]:
        target = era.strip().lower()
        return [e for e in self.get_all_events() if self.get_event_era(e).lower() == target]

    def get_era_counts(self) -> dict[str, int]:
        return {era: len(events) for era, events in self.get_eras().items()}
