"""中转站 CRUD + 模型拉取 + 批量测试 API。"""
import uuid
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from .. import adapters, storage
from ..schemas import StationCreate, StationUpdate, TestRequest

router = APIRouter(prefix="/api/stations", tags=["stations"])


def _mask_key(key: str) -> str:
    if len(key) <= 8:
        return "******"
    return key[:4] + "******" + key[-4:]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _to_out(station: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": station["id"],
        "name": station["name"],
        "base_url": station["base_url"],
        "api_key_masked": _mask_key(station["api_key"]),
        "protocol": station.get("protocol", "auto"),
        "created_at": station.get("created_at", ""),
        "updated_at": station.get("updated_at", ""),
    }


def _find(stations: List[Dict[str, Any]], sid: str) -> Dict[str, Any]:
    for s in stations:
        if s["id"] == sid:
            return s
    raise HTTPException(status_code=404, detail="中转站不存在")


@router.get("")
async def list_stations() -> List[Dict[str, Any]]:
    stations = await run_in_threadpool(storage.load_stations)
    return [_to_out(s) for s in stations]


@router.post("", status_code=201)
async def create_station(body: StationCreate) -> Dict[str, Any]:
    now = _now()
    station = {
        "id": uuid.uuid4().hex,
        "name": body.name.strip(),
        "base_url": body.base_url.strip(),
        "api_key": body.api_key.strip(),
        "protocol": body.protocol,
        "created_at": now,
        "updated_at": now,
    }
    stations = await run_in_threadpool(storage.load_stations)
    stations.append(station)
    await run_in_threadpool(storage.save_stations, stations)
    return _to_out(station)


@router.put("/{sid}")
async def update_station(sid: str, body: StationUpdate) -> Dict[str, Any]:
    stations = await run_in_threadpool(storage.load_stations)
    station = _find(stations, sid)
    if body.name is not None and body.name.strip():
        station["name"] = body.name.strip()
    if body.base_url is not None and body.base_url.strip():
        station["base_url"] = body.base_url.strip()
    if body.api_key is not None and body.api_key.strip():
        station["api_key"] = body.api_key.strip()
    if body.protocol is not None:
        station["protocol"] = body.protocol
    station["updated_at"] = _now()
    await run_in_threadpool(storage.save_stations, stations)
    return _to_out(station)


@router.delete("/{sid}", status_code=204)
async def delete_station(sid: str) -> None:
    stations = await run_in_threadpool(storage.load_stations)
    station = _find(stations, sid)
    stations.remove(station)
    await run_in_threadpool(storage.save_stations, stations)


@router.post("/{sid}/models")
async def get_models(sid: str) -> Dict[str, Any]:
    stations = await run_in_threadpool(storage.load_stations)
    station = _find(stations, sid)
    return await adapters.list_models(
        station["base_url"], station["api_key"], station.get("protocol", "auto")
    )


@router.post("/{sid}/test")
async def test_station(sid: str, body: TestRequest) -> Dict[str, Any]:
    stations = await run_in_threadpool(storage.load_stations)
    station = _find(stations, sid)
    protocol = station.get("protocol", "auto")

    # 1) 确定协议：auto 时先探测
    fetched_models: List[str] = []
    if protocol == "auto":
        probe = await adapters.list_models(station["base_url"], station["api_key"], "auto")
        if probe.get("error"):
            return {
                "protocol": "auto", "models": [], "total": 0, "available": 0,
                "results": [], "error": probe["error"],
            }
        protocol = probe["protocol"]
        fetched_models = probe["models"]

    # 2) 确定要测试的模型列表
    if body.models:
        models = list(body.models)
    elif fetched_models:
        models = fetched_models
    else:
        probe = await adapters.list_models(station["base_url"], station["api_key"], protocol)
        if probe.get("error"):
            return {
                "protocol": protocol, "models": [], "total": 0, "available": 0,
                "results": [], "error": probe["error"],
            }
        models = probe["models"]

    if not models:
        return {
            "protocol": protocol, "models": [], "total": 0, "available": 0,
            "results": [], "error": "没有可测试的模型",
        }

    results = await adapters.test_models(station["base_url"], station["api_key"], protocol, models)
    available = sum(1 for r in results if r["available"])
    return {
        "protocol": protocol,
        "models": models,
        "total": len(results),
        "available": available,
        "results": results,
    }
