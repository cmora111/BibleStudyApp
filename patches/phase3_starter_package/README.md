# Phase 3 Starter Package — Bible Timeline + Map (Visual)

This starter package adds the foundation for:
- Bible event timeline dataset
- timeline engine
- folium-based map exporter
- bridge hooks from timeline events into your knowledge graph

## Included files
- `app/engines/timeline_engine.py`
- `app/engines/map_engine.py`
- `app/engines/event_graph_bridge.py`
- `data/timeline_events.csv`

## Quick start

Copy the files into your project:

```bash
cp -r phase3_starter_package/app ~/Bible/BibleStudyApp/ultimate_bible_app_latest/
cp phase3_starter_package/data/timeline_events.csv ~/Bible/BibleStudyApp/ultimate_bible_app_latest/data/
```

## Optional dependency

The map exporter uses `folium`.

```bash
pip install folium
```
