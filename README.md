# Solaris3 Prototype

Run the game loop from the repo root:

```
python -m game
```

Runs are stored as TinyDB JSON files under `data/`:

- `data/run_<run_id>.json`

GameState fields:

- tension
- ocean_activity
- crew_load
- earth_pressure
- station_power
- turn

Docs:

- Instrument Specialist: `docs/instrument_specialist.md`
- Crew Officer: `docs/crew_officer.md`
