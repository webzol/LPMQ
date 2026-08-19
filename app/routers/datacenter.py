"""数据中心聚合 API。"""
from typing import Any, Dict

from fastapi import APIRouter

from .. import aggregate

router = APIRouter(prefix="/api/datacenter", tags=["datacenter"])


@router.post("/aggregate")
async def aggregate_datacenter() -> Dict[str, Any]:
    """聚合所有中转站的模型及其可用性。"""
    return await aggregate.aggregate_all()
