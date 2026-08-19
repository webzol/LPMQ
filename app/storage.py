"""中转站配置的 JSON 文件读写（含并发锁与原子写）。"""
import json
import threading
from typing import Any, Dict, List

from .config import DATA_DIR, STATIONS_FILE

_lock = threading.Lock()


def _ensure_file() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not STATIONS_FILE.exists():
        STATIONS_FILE.write_text("[]", encoding="utf-8")


def load_stations() -> List[Dict[str, Any]]:
    """读取全部中转站，返回 list[dict]。"""
    _ensure_file()
    with _lock:
        data = json.loads(STATIONS_FILE.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def save_stations(stations: List[Dict[str, Any]]) -> None:
    """原子写入全部中转站（先写临时文件再替换，避免损坏）。"""
    _ensure_file()
    with _lock:
        tmp = STATIONS_FILE.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(stations, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tmp.replace(STATIONS_FILE)
