from __future__ import annotations

from pathlib import Path

from app.engines.timeline_engine import BibleTimelineEngine

try:
    import folium
    from folium.plugins import MarkerCluster
except Exception as exc:
    folium = None
    MarkerCluster = None
    _FOLIUM_IMPORT_ERROR = exc
else:
    _FOLIUM_IMPORT_ERROR = None


class BibleMapEngine:
    def __init__(self, csv_path: str | Path):
        self.csv_path = Path(csv_path)
        self.timeline = BibleTimelineEngine(self.csv_path)

    def export_map(
        self,
        output_path: str | Path,
        *,
        title: str = "Bible Timeline Map",
        only_with_coordinates: bool = True,
    ) -> str:
        if folium is None:
            raise RuntimeError(
                "folium is required for map export. Install it with: pip install folium"
            ) from _FOLIUM_IMPORT_ERROR

        output = Path(output_path)
        events = self.timeline.get_all_events()
        if only_with_coordinates:
            events = [e for e in events if e.has_coordinates]

        bible_map = folium.Map(location=[31.5, 35.0], zoom_start=6, control_scale=True)
        cluster = MarkerCluster(name="Events").add_to(bible_map)

        for event in events:
            popup_html = f"""
            <b>{event.title}</b><br>
            <b>Reference:</b> {event.reference}<br>
            <b>Time:</b> {event.time_label}<br>
            <b>Place:</b> {event.location_name}<br>
            <b>People:</b> {", ".join(event.people) if event.people else "N/A"}<br>
            <b>Tags:</b> {", ".join(event.tags) if event.tags else "N/A"}<br>
            <b>Summary:</b> {event.summary}
            """
            folium.Marker(
                location=[event.latitude, event.longitude],
                popup=folium.Popup(popup_html, max_width=420),
                tooltip=event.title,
            ).add_to(cluster)

        folium.LayerControl().add_to(bible_map)
        output.parent.mkdir(parents=True, exist_ok=True)
        bible_map.save(str(output))
        return str(output)

    def export_single_event_map(
        self,
        output_path: str | Path,
        *,
        event,
        include_nearby: bool = True,
    ) -> str:
        if folium is None:
            raise RuntimeError(
                "folium is required for map export. Install it with: pip install folium"
            ) from _FOLIUM_IMPORT_ERROR

        if event.latitude is None or event.longitude is None:
            raise ValueError("Selected event does not have coordinates.")

        output = Path(output_path)
        bible_map = folium.Map(
            location=[event.latitude, event.longitude],
            zoom_start=9,
            control_scale=True,
        )

        popup_html = f"""
        <b>{event.title}</b><br>
        <b>Reference:</b> {event.reference}<br>
        <b>Time:</b> {event.time_label}<br>
        <b>Place:</b> {event.location_name}<br>
        <b>People:</b> {", ".join(event.people) if event.people else "N/A"}<br>
        <b>Tags:</b> {", ".join(event.tags) if event.tags else "N/A"}<br>
        <b>Summary:</b> {event.summary}
        """

        folium.Marker(
            location=[event.latitude, event.longitude],
            popup=folium.Popup(popup_html, max_width=420),
            tooltip=f"{event.title} (selected)",
        ).add_to(bible_map)

        if include_nearby:
            for other in self.timeline.get_all_events():
                if other.id == event.id or not other.has_coordinates:
                    continue
                if abs(other.latitude - event.latitude) <= 1.5 and abs(other.longitude - event.longitude) <= 1.5:
                    other_popup = f"{other.title}<br>{other.reference}<br>{other.summary}"
                    folium.CircleMarker(
                        location=[other.latitude, other.longitude],
                        radius=5,
                        popup=folium.Popup(other_popup, max_width=320),
                        tooltip=other.title,
                    ).add_to(bible_map)

        output.parent.mkdir(parents=True, exist_ok=True)
        bible_map.save(str(output))
        return str(output)
