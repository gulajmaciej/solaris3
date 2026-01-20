"""TinyDB-backed run storage."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from tinydb import Query, TinyDB


class TinyDBRunStore:
    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self._data_dir = data_dir or Path("data")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._db_cache: Dict[str, TinyDB] = {}

    def _get_db(self, run_id: str) -> TinyDB:
        if run_id not in self._db_cache:
            path = self._data_dir / f"run_{run_id}.json"
            self._db_cache[run_id] = TinyDB(path)
        return self._db_cache[run_id]

    def create_run(self, seed: int) -> str:
        run_id = uuid4().hex
        db = self._get_db(run_id)
        meta = db.table("meta")
        created_at = datetime.now(timezone.utc).isoformat()
        meta.insert(
            {
                "run_id": run_id,
                "seed": seed,
                "created_at": created_at,
                "ended": False,
            }
        )
        return run_id

    def append_event(self, run_id: str, event_dict: Dict[str, Any]) -> None:
        db = self._get_db(run_id)
        db.table("events").insert(event_dict)

    def save_turn_snapshot(self, run_id: str, turn: int, state_dict: Dict[str, Any]) -> None:
        db = self._get_db(run_id)
        db.table("turns").insert({"turn": turn, "state": state_dict})

    def save_agent_memory(self, run_id: str, agent_id: str, key: str, value_dict: Dict[str, Any]) -> None:
        db = self._get_db(run_id)
        table = db.table("agent_memory")
        query = Query()
        table.upsert(
            {"agent_id": agent_id, "key": key, "value": value_dict},
            (query.agent_id == agent_id) & (query.key == key),
        )

    def load_agent_memory(self, run_id: str, agent_id: str, key: str) -> Optional[Dict[str, Any]]:
        db = self._get_db(run_id)
        query = Query()
        result = db.table("agent_memory").get((query.agent_id == agent_id) & (query.key == key))
        if result is None:
            return None
        return result.get("value")

    def finalize_run(
        self,
        run_id: str,
        ending_id: str,
        ending_title: str,
        turn: int,
        final_state_dict: Dict[str, Any],
    ) -> None:
        db = self._get_db(run_id)
        meta = db.table("meta")
        query = Query()
        meta.update(
            {
                "ended": True,
                "ending_id": ending_id,
                "ending_title": ending_title,
                "final_turn": turn,
                "final_state": final_state_dict,
            },
            query.run_id == run_id,
        )
