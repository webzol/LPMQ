"""OpenAI / Anthropic 协议适配：拉取模型列表 + 实测模型。"""
import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .config import TEST_CONCURRENCY, TEST_MESSAGE, TEST_MAX_TOKENS, TEST_TIMEOUT


def normalize_base_url(base_url: str) -> str:
    """规范化地址：去掉末尾斜杠，若不以 /v1 结尾则自动补齐。"""
    base_url = base_url.strip().rstrip("/")
    if not base_url.endswith("/v1"):
        base_url += "/v1"
    return base_url


def _openai_headers(api_key: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _anthropic_headers(api_key: str) -> Dict[str, str]:
    return {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }


def _parse_models(data: Any) -> List[str]:
    """从 /v1/models 响应中提取模型 id 列表。"""
    if not isinstance(data, dict):
        return []
    items = data.get("data")
    if not isinstance(items, list):
        return []
    return [it["id"] for it in items if isinstance(it, dict) and it.get("id")]


async def _get_models(
    client: httpx.AsyncClient, base: str, headers: Dict[str, str]
) -> Tuple[List[str], Optional[str]]:
    try:
        resp = await client.get(f"{base}/models", headers=headers)
    except httpx.RequestError as e:
        return [], f"请求失败: {e}"
    if resp.status_code != 200:
        return [], f"HTTP {resp.status_code}: {resp.text[:200]}"
    try:
        data = resp.json()
    except ValueError:
        return [], "响应不是有效 JSON"
    return _parse_models(data), None


async def list_models(
    base_url: str, api_key: str, protocol: str = "auto"
) -> Dict[str, Any]:
    """拉取模型列表。返回 {protocol, models, error}。"""
    base = normalize_base_url(base_url)
    async with httpx.AsyncClient(timeout=TEST_TIMEOUT, follow_redirects=True) as client:
        if protocol == "openai":
            models, err = await _get_models(client, base, _openai_headers(api_key))
            return {"protocol": "openai", "models": models, "error": err}
        if protocol == "anthropic":
            models, err = await _get_models(client, base, _anthropic_headers(api_key))
            return {"protocol": "anthropic", "models": models, "error": err}

        # auto：先按 OpenAI 探测，失败再按 Anthropic
        models, err = await _get_models(client, base, _openai_headers(api_key))
        if err is None:
            return {"protocol": "openai", "models": models, "error": None}
        openai_err = err
        models, err = await _get_models(client, base, _anthropic_headers(api_key))
        if err is None:
            return {"protocol": "anthropic", "models": models, "error": None}
        return {
            "protocol": "auto",
            "models": [],
            "error": f"OpenAI 方式: {openai_err} / Anthropic 方式: {err}",
        }


async def _test_one(
    client: httpx.AsyncClient,
    base: str,
    headers: Dict[str, str],
    model: str,
    path: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    start = time.perf_counter()
    try:
        resp = await client.post(f"{base}/{path}", headers=headers, json=payload)
    except httpx.RequestError as e:
        return {"model": model, "available": False, "latency_ms": None, "error": f"请求失败: {e}"}
    latency_ms = int((time.perf_counter() - start) * 1000)
    if resp.status_code == 200:
        return {"model": model, "available": True, "latency_ms": latency_ms, "error": None}
    return {
        "model": model,
        "available": False,
        "latency_ms": latency_ms,
        "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
    }


async def test_models(
    base_url: str, api_key: str, protocol: str, models: List[str]
) -> List[Dict[str, Any]]:
    """并发实测多个模型，返回逐个结果列表。protocol 需为 openai 或 anthropic。"""
    base = normalize_base_url(base_url)
    is_anthropic = protocol == "anthropic"
    headers = _anthropic_headers(api_key) if is_anthropic else _openai_headers(api_key)
    sem = asyncio.Semaphore(TEST_CONCURRENCY)

    async with httpx.AsyncClient(timeout=TEST_TIMEOUT, follow_redirects=True) as client:

        async def run(model: str) -> Dict[str, Any]:
            async with sem:
                if is_anthropic:
                    return await _test_one(
                        client, base, headers, model, "messages",
                        {
                            "model": model,
                            "max_tokens": TEST_MAX_TOKENS,
                            "messages": [{"role": "user", "content": TEST_MESSAGE}],
                        },
                    )
                return await _test_one(
                    client, base, headers, model, "chat/completions",
                    {
                        "model": model,
                        "messages": [{"role": "user", "content": TEST_MESSAGE}],
                        "max_tokens": TEST_MAX_TOKENS,
                    },
                )

        return list(await asyncio.gather(*(run(m) for m in models)))
