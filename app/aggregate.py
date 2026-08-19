"""数据中心聚合逻辑：跨中转站聚合模型可用性。"""
import asyncio
from typing import Any, Dict, List

from . import adapters, storage


async def _aggregate_station(station: Dict[str, Any]) -> Dict[str, Any]:
    """聚合单个中转站：探测协议、拉取模型、实测全部模型。"""
    sid = station["id"]
    name = station["name"]
    base_url = station["base_url"]
    api_key = station["api_key"]
    protocol = station.get("protocol", "auto")

    # 拉取模型列表（auto 时自动探测协议）
    probe = await adapters.list_models(base_url, api_key, protocol)
    if probe.get("error"):
        return {
            "station_id": sid,
            "station": name,
            "error": probe["error"],
            "results": [],
        }
    resolved_protocol = probe["protocol"] if protocol == "auto" else protocol
    models = list(dict.fromkeys(probe["models"]))  # 去重保序

    if not models:
        return {
            "station_id": sid,
            "station": name,
            "error": None,
            "results": [],
        }

    results = await adapters.test_models(base_url, api_key, resolved_protocol, models)
    return {
        "station_id": sid,
        "station": name,
        "error": None,
        "results": results,
    }


async def aggregate_all() -> Dict[str, Any]:
    """聚合所有中转站，按模型分组返回可用性。"""
    stations = storage.load_stations()
    station_list = [{"id": s["id"], "name": s["name"]} for s in stations]

    if not stations:
        return {"stations": [], "models": [], "errors": []}

    per_station = await asyncio.gather(*(_aggregate_station(s) for s in stations))

    model_map: Dict[str, Dict[str, Any]] = {}
    errors: List[str] = []

    for st in per_station:
        if st["error"]:
            errors.append(f"{st['station']}: {st['error']}")
            continue
        for r in st["results"]:
            model = r["model"]
            entry = model_map.setdefault(
                model,
                {
                    "model": model,
                    "total": 0,
                    "available": 0,
                    "unavailable": 0,
                    "per_station": [],
                },
            )
            entry["total"] += 1
            entry["per_station"].append(
                {
                    "station_id": st["station_id"],
                    "station": st["station"],
                    "available": r["available"],
                    "latency_ms": r.get("latency_ms"),
                    "error": r.get("error"),
                }
            )
            if r["available"]:
                entry["available"] += 1
            else:
                entry["unavailable"] += 1

    models: List[Dict[str, Any]] = []
    for entry in model_map.values():
        if entry["unavailable"] == 0:
            entry["status"] = "available"
        elif entry["available"] == 0:
            entry["status"] = "unavailable"
        else:
            entry["status"] = "partial"
        models.append(entry)

    order = {"available": 0, "partial": 1, "unavailable": 2}
    models.sort(key=lambda m: (order.get(m["status"], 3), m["model"].lower()))

    return {"stations": station_list, "models": models, "errors": errors}
