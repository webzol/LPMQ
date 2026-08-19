"""Pydantic 数据模型。"""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

# 协议类型：auto=自动探测，openai=OpenAI 兼容，anthropic=Anthropic 兼容
Protocol = Literal["auto", "openai", "anthropic"]


class StationCreate(BaseModel):
    """新增/全量更新中转站时的请求体。"""

    name: str = Field(..., min_length=1, max_length=100, description="中转站名称")
    base_url: str = Field(..., min_length=1, max_length=500, description="中转站地址")
    api_key: str = Field(..., min_length=1, max_length=500, description="API 密钥")
    protocol: Protocol = "auto"


class StationUpdate(BaseModel):
    """更新中转站时的请求体；api_key 留空表示保持不变。"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    base_url: Optional[str] = Field(None, min_length=1, max_length=500)
    api_key: Optional[str] = Field(None, max_length=500)
    protocol: Optional[Protocol] = None


class TestRequest(BaseModel):
    """模型测试请求体，models 缺省表示测试全部模型。"""

    models: Optional[List[str]] = None
