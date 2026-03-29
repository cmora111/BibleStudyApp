
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.engines.timeline_engine import BibleTimelineEngine


@dataclass(slots=True)
class EventGraphNode:
    id: str
    label: str
    node_type: str
    metadata: dict


@dataclass(slots=True)
class EventGraphEdge:
    source: str
    target: str
    relation: str


class EventGraphBridge:
    def __init__(self, csv_path: str | Path):
        self.timeline = BibleTimelineEngine(csv_path)

    def event_to_graph_bundle(self, event_id: str):
        event = next((e for e in self.timeline.get_all_events() if e.id == event_id), None)
        if event is None:
            return [], []

        nodes = []
        edges = []

        event_node_id = f"event:{event.id}"
        nodes.append(EventGraphNode(
            id=event_node_id,
            label=event.title,
            node_type="event",
            metadata={
                "reference": event.reference,
                "time_label": event.time_label,
                "summary": event.summary,
                "location": event.location_name,
                "event_type": event.event_type,
            },
        ))

        for person in event.people:
            person_id = f"person:{person.lower().replace(' ', '_')}"
            nodes.append(EventGraphNode(id=person_id, label=person, node_type="person", metadata={}))
            edges.append(EventGraphEdge(source=event_node_id, target=person_id, relation="involves"))

        if event.location_name:
            loc_id = f"place:{event.location_name.lower().replace(' ', '_')}"
            nodes.append(EventGraphNode(
                id=loc_id,
                label=event.location_name,
                node_type="place",
                metadata={"latitude": event.latitude, "longitude": event.longitude},
            ))
            edges.append(EventGraphEdge(source=event_node_id, target=loc_id, relation="occurred_at"))

        for tag in event.tags:
            tag_id = f"theme:{tag.lower().replace(' ', '_')}"
            nodes.append(EventGraphNode(id=tag_id, label=tag, node_type="theme", metadata={}))
            edges.append(EventGraphEdge(source=event_node_id, target=tag_id, relation="tagged_with"))

        ref_id = f"ref:{event.book.lower()}_{event.chapter_start}_{event.verse_start}"
        nodes.append(EventGraphNode(id=ref_id, label=event.reference, node_type="reference", metadata={}))
        edges.append(EventGraphEdge(source=event_node_id, target=ref_id, relation="anchored_in"))

        uniq = {}
        for node in nodes:
            uniq[node.id] = node
        return list(uniq.values()), edges
