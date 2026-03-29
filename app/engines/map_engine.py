from pathlib import Path
import folium


class BibleMapEngine:
    def __init__(self, *args, **kwargs):
        self.cache = {}
        self.base_map = None

    # ---------- Base Map (cached) ----------
    def _get_base_map(self):
        if self.base_map:
            return self.base_map

        self.base_map = folium.Map(
            location=[31.5, 35.0],
            zoom_start=6,
            tiles="CartoDB positron"  # clean English tiles
        )
        return self.base_map

    # ---------- Single Event Map ----------
    def export_single_event_map(self, output_file, event, include_nearby=True):
        cache_key = f"event:{event.id}"

        if cache_key in self.cache:
            return self.cache[cache_key]

        m = folium.Map(
            location=[event.latitude or 31.5, event.longitude or 35.0],
            zoom_start=7,
            tiles="CartoDB positron"
        )

        # Main marker (RED for visibility)
        if event.latitude and event.longitude:
            folium.Marker(
                [event.latitude, event.longitude],
                popup=f"<b>{event.title}</b><br>{event.reference}",
                tooltip=event.title,
                icon=folium.Icon(color="red", icon="info-sign")
            ).add_to(m)

        # Nearby markers (optional)
        if include_nearby and hasattr(event, "nearby_events"):
            for e in event.nearby_events:
                if e.latitude and e.longitude:
                    folium.CircleMarker(
                        [e.latitude, e.longitude],
                        radius=4,
                        color="blue",
                        fill=True
                    ).add_to(m)

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        m.save(output_path)

        self.cache[cache_key] = str(output_path)
        return str(output_path)

    # ---------- Full Timeline Map ----------
    def export_map(self, output_file):
        cache_key = "full_map"

        if cache_key in self.cache:
            return self.cache[cache_key]

        m = self._get_base_map()

        # NOTE: this assumes you inject events externally if needed
        # (keep this lightweight to avoid slowdown)

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        m.save(output_path)

        self.cache[cache_key] = str(output_path)
        return str(output_path)

    # ---------- Lightweight Preview ----------
    def export_location_subset(self, events, output_file):
        cache_key = f"subset:{len(events)}"

        if cache_key in self.cache:
            return self.cache[cache_key]

        m = folium.Map(
            location=[31.5, 35.0],
            zoom_start=6,
            tiles="CartoDB positron"
        )

        for event in events:
            if event.latitude and event.longitude:
                folium.CircleMarker(
                    [event.latitude, event.longitude],
                    radius=5,
                    color="green",
                    fill=True,
                    tooltip=event.title
                ).add_to(m)

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        m.save(output_path)

        self.cache[cache_key] = str(output_path)
        return str(output_path)
