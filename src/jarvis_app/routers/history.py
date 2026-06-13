"""历史记录 API"""
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class HistoryItem(BaseModel):
    id: int
    type: Literal["prep", "training"]
    title: str
    date: str
    industry: str
    score: int | None = None

HISTORY_DATA = [
    {"id":1,"type":"prep","title":"某金融机构移动安全方案","date":"2026-06-12","industry":"金融"},
    {"id":2,"type":"prep","title":"政务云等保合规方案","date":"2026-06-11","industry":"政府"},
    {"id":3,"type":"training","title":"金融-预算敏感型模拟训练","date":"2026-06-10","industry":"金融","score":78},
    {"id":4,"type":"training","title":"医疗-技术专家型模拟训练","date":"2026-06-09","industry":"医疗","score":82},
    {"id":5,"type":"prep","title":"医疗数据安全治理方案","date":"2026-06-08","industry":"医疗"},
    {"id":6,"type":"training","title":"零售-随机性格模拟训练","date":"2026-06-07","industry":"零售","score":65},
]

@router.get("/items")
async def get_history():
    """获取历史记录列表"""
    return {"items": HISTORY_DATA, "total": len(HISTORY_DATA)}

@router.delete("/items/{item_id}")
async def delete_history_item(item_id: int):
    """删除历史记录"""
    return {"message": f"Item {item_id} deleted"}
