"""知识库 API — 从 YAML 真实数据加载，全部中文输出"""

import sys
from pathlib import Path

from fastapi import APIRouter, Query
from pydantic import BaseModel

# 确保 jarvis 模块可被找到
SRC_DIR = Path(__file__).resolve().parent.parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from jarvis.knowledge.loader import KnowledgeBase, load_all  # noqa: E402

router = APIRouter()

# ── 行业中文映射 ──
INDUSTRY_CN = {
    "finance": "金融",
    "healthcare": "医疗",
    "manufacturing": "制造业",
    "government": "政务",
    "education": "教育",
    "retail": "零售",
}

# ── 场景中文映射 ──
SCENARIO_CN = {
    "compliance": "合规审计",
    "data_leak": "数据泄露",
    "ransomware": "勒索软件",
    "apt": "高级持续性威胁",
    "phishing": "钓鱼攻击",
}

# ── 缓存知识库实例 ──
_kb_cache: KnowledgeBase | None = None

def _get_kb() -> KnowledgeBase:
    global _kb_cache
    if _kb_cache is None:
        _kb_cache = load_all()
    return _kb_cache

def _reload_kb():
    global _kb_cache
    _kb_cache = load_all()
    return _kb_cache


# ── 响应模型 ──

class CaseItem(BaseModel):
    id: str
    industry: str
    industry_cn: str
    scenario: str
    scenario_cn: str
    title: str
    surface_pain: str
    deep_pain: str
    solution_method: str
    solution_product: str
    solution_phases: list[str]
    sensitivity: list[str]
    reference_event: str | None = None

class MethodologyItem(BaseModel):
    id: str
    name: str
    description: str
    applicable_scenarios_cn: list[str]
    steps: list[dict]
    industry_match_cn: list[str]

class SensitivityItem(BaseModel):
    id: str
    industry: str
    industry_cn: str
    primary_sensitivity: str
    secondary_sensitivities: list[str]
    landmines: list[str]
    empathy_phrases: list[str]

class ProductItem(BaseModel):
    id: str
    name: str
    category: str
    description: str
    key_features: list[str]
    applicable_industries_cn: list[str]
    applicable_scenarios_cn: list[str]

class KnowledgeResponse(BaseModel):
    cases: list[CaseItem]
    methodologies: list[MethodologyItem]
    sensitivities: list[SensitivityItem]
    products: list[ProductItem]
    total: int


# ── 路由 ──

@router.get("/items", response_model=KnowledgeResponse)
async def get_knowledge(
    type: str | None = Query(default=None, description="筛选类型: cases/methodologies/sensitivities/products"),
    search: str | None = Query(default=None, description="搜索关键词"),
):
    """获取知识库全部条目，支持按类型筛选和搜索"""
    kb = _get_kb()

    cases_list = [
        CaseItem(
            id=c.id,
            industry=c.industry,
            industry_cn=INDUSTRY_CN.get(c.industry, c.industry),
            scenario=c.scenario,
            scenario_cn=SCENARIO_CN.get(c.scenario, c.scenario),
            title=f"{INDUSTRY_CN.get(c.industry, c.industry)}行业{SCENARIO_CN.get(c.scenario, c.scenario)}案例",
            surface_pain=c.pain_points.surface,
            deep_pain=c.pain_points.deep,
            solution_method=c.solution.method,
            solution_product=c.solution.product,
            solution_phases=c.solution.phases,
            sensitivity=c.sensitivity,
            reference_event=c.reference_event,
        ) for c in kb.cases
    ]

    methods_list = [
        MethodologyItem(
            id=m.id,
            name=m.name,
            description=m.description,
            applicable_scenarios_cn=[SCENARIO_CN.get(s, s) for s in m.applicable_scenarios],
            steps=[{"order": s.order, "title": s.title, "description": s.description, "key_actions": s.key_actions} for s in m.steps],
            industry_match_cn=[INDUSTRY_CN.get(i, i) for i in m.industry_match],
        ) for m in kb.methodologies
    ]

    sens_list = [
        SensitivityItem(
            id=s.id,
            industry=s.industry,
            industry_cn=INDUSTRY_CN.get(s.industry, s.industry),
            primary_sensitivity=s.primary_sensitivity,
            secondary_sensitivities=s.secondary_sensitivities,
            landmines=s.landmines,
            empathy_phrases=s.empathy_phrases,
        ) for s in kb.sensitivities
    ]

    products_list = [
        ProductItem(
            id=p.id,
            name=p.name,
            category=p.category,
            description=p.description,
            key_features=p.key_features,
            applicable_industries_cn=[INDUSTRY_CN.get(i, i) for i in p.applicable_industries],
            applicable_scenarios_cn=[SCENARIO_CN.get(s, s) for s in p.applicable_scenarios],
        ) for p in kb.products
    ]

    # 按类型筛选
    if type and type != "all":
        if type == "cases":
            methods_list, sens_list, products_list = [], [], []
        elif type == "methodologies":
            cases_list, sens_list, products_list = [], [], []
        elif type == "sensitivities":
            cases_list, methods_list, products_list = [], [], []
        elif type == "products":
            cases_list, methods_list, sens_list = [], [], []

    # 搜索
    if search:
        sl = search.lower()
        cases_list = [c for c in cases_list if sl in c.title.lower() or sl in c.surface_pain.lower() or sl in c.deep_pain.lower()]
        methods_list = [m for m in methods_list if sl in m.name.lower() or sl in m.description.lower()]
        sens_list = [s for s in sens_list if sl in s.industry_cn.lower() or sl in s.primary_sensitivity.lower()]
        products_list = [p for p in products_list if sl in p.name.lower() or sl in p.description.lower()]

    return KnowledgeResponse(
        cases=cases_list,
        methodologies=methods_list,
        sensitivities=sens_list,
        products=products_list,
        total=len(cases_list) + len(methods_list) + len(sens_list) + len(products_list),
    )


@router.get("/stats")
async def get_knowledge_stats():
    """获取知识库统计信息"""
    kb = _get_kb()
    return {
        "cases": len(kb.cases),
        "methodologies": len(kb.methodologies),
        "sensitivities": len(kb.sensitivities),
        "products": len(kb.products),
        "total": len(kb.cases) + len(kb.methodologies) + len(kb.sensitivities) + len(kb.products),
    }


@router.post("/reload")
async def reload_knowledge():
    """强制重新加载知识库"""
    kb = _reload_kb()
    return {
        "message": "知识库已重新加载",
        "cases": len(kb.cases),
        "methodologies": len(kb.methodologies),
        "sensitivities": len(kb.sensitivities),
        "products": len(kb.products),
    }
