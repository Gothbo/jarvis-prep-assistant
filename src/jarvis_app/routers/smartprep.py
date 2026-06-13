"""智能售前准备 API"""
import asyncio

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class SmartPrepRequest(BaseModel):
    scenario: str = Field(..., min_length=10, description="客户场景描述")
    industry: str | None = Field(default=None, description="行业（可选）")


class SmartPrepResponse(BaseModel):
    industry: str
    scenario: str
    summary: str
    key_points: list[str]
    products: list[str]
    next_steps: str


@router.post("/generate", response_model=SmartPrepResponse)
async def generate_prep(request: SmartPrepRequest):
    """根据客户场景生成售前准备方案"""
    # 模拟生成延迟
    await asyncio.sleep(1.5)

    return SmartPrepResponse(
        industry=request.industry or "金融",
        scenario=request.scenario[:30] + "..." if len(request.scenario) > 30 else request.scenario,
        summary="针对某金融机构移动银行应用的售前准备方案，涵盖API安全防护、数据隐私保护与合规审计三大核心需求。",
        key_points=[
            "客户面临移动银行API安全风险、权限管理混乱、合规审计差距三大核心痛点",
            "推荐方案组合：WAF/Web防护 + 零信任架构 + XDR/SIEM平台",
            "竞争优势：全栈国产化、金融行业最佳实践、6个月内可通过审计"
        ],
        products=["WAF/Web安全防护", "零信任安全架构", "XDR/SIEM 解决方案"],
        next_steps="建议安排一次技术交流会，针对客户现有IT环境进行兼容性评估，并输出详细的实施路线图。"
    )
