"""确定性本地引擎（无 Key 也能跑通的核心）。

提供四类能力：
  - classify(text)        关键词打分分类
  - understand(text)      正则抽取诉求要素
  - work_order(...)       模板化工单
  - reply(...)            模板化回复辅助

分类使用 12 类关键词字典打分；理解使用正则提取时间/地点/人员/事件/诉求等。
"""
from __future__ import annotations

import random
import re
from datetime import datetime
from typing import Optional

from app.data import loaders
from app.schemas.models import (
    ClassificationResult,
    DepartmentSuggestion,
    ReplyResult,
    UnderstandingResult,
    WorkOrder,
)

# ---------------------------------------------------------------------------
# 12 类关键词字典（可扩充）。code 与 category_catalog.json 保持一致。
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "economic_trade": ["价格", "收费", "经营", "消费", "发票", "商家", "商场", "市场经营"],
    "health": ["医院", "挂号", "诊疗", "医疗", "卫生", "疫苗", "门诊", "卫生院", "护士"],
    "market_regulation": [
        "营业执照", "公示", "价格公示", "假冒", "食品", "计量", "电梯",
        "消费维权", "无证", "经营许可",
    ],
    "ecology_environment": [
        "污染", "异味", "扬尘", "油烟", "排污", "噪声", "水体", "废气", "环保",
    ],
    "public_service": [
        "水", "电", "气", "供暖", "供热", "宽带", "自来水", "燃气公司", "供电",
    ],
    "urban_rural_construction": [
        "房屋", "施工", "工地", "拆迁", "危房", "路灯", "道路", "物业", "建房", "小区设施",
    ],
    "public_safety": [
        "燃气泄漏", "燃气", "泄漏", "安全", "消防", "治安", "报警", "危化", "防溺水", "抢险", "应急",
    ],
    "labor_social_security": [
        "工资", "拖欠", "社保", "工伤", "劳动合同", "退休", "就业", "劳动", "辞职", "仲裁",
    ],
    "transportation": [
        "公交", "线路", "出租车", "拥堵", "停车", "车站", "道路", "驾照", "交管", "地铁",
    ],
    "science_education_culture_sports": [
        "学校", "教育", "补课", "文化", "旅游", "体育", "场馆", "图书馆", "补课班", "景区",
    ],
    "agriculture_forestry_water_land": [
        "农田", "灌溉", "养殖", "土地承包", "河湖", "水库", "耕地", "林", "农业", "畜牧",
    ],
    "urban_management": [
        "垃圾", "占道经营", "占用经营", "占道", "违建", "绿化", "井盖", "噪声", "共享单车", "流浪", "市政",
    ],
}

# 紧急 / 重复 触发词
URGENT_WORDS = ["燃气泄漏", "泄漏", "安全", "火", "危险", "危化", "紧急", "立即", "加急", "报警", "抢险"]
REPEAT_WORDS = ["再次", "上次", "此前反映", "历史工单", "此前", "重新反映", "仍"]

_CODE_TO_NAME = loaders.category_code_to_name()
_NAME_TO_CODE = loaders.category_name_to_code()


# ---------------------------------------------------------------------------
# 分类
# ---------------------------------------------------------------------------
def score_categories(text: str) -> list[tuple[str, str, float, list[str]]]:
    """对 12 类打分（关键词按长度加权，多字词优先），返回 [(code, name, score, hits), ...] 降序。"""
    results: list[tuple[str, str, float, list[str]]] = []
    for code, kws in CATEGORY_KEYWORDS.items():
        hits = [kw for kw in kws if kw in text]
        # 加权：长关键词权重大，提升歧义场景下的精确度
        score = sum(len(kw) for kw in hits)
        results.append((code, _CODE_TO_NAME.get(code, code), score, hits))
    results.sort(key=lambda x: x[2], reverse=True)
    return results


def classify_full(text: str) -> dict:
    """返回分类完整结果（含 needs_manual、keywords_hit）。"""
    scored = score_categories(text)
    best_code, best_name, best_score, best_hits = scored[0]
    # 判断是否并列
    tied = any(s[2] == best_score and s[0] != best_code for s in scored)
    needs_manual = (best_score <= 1) or tied
    total_weight = sum(len(kw) for kw in CATEGORY_KEYWORDS.get(best_code, [])) or 1
    confidence = round(best_score / total_weight, 3) if best_score > 0 else 0.0
    return {
        "category_code": best_code if best_score > 0 else None,
        "category_name": best_name if best_score > 0 else None,
        "confidence": confidence,
        "keywords_hit": best_hits,
        "needs_manual": needs_manual,
        "scores": scored,
    }


def classify(text: str) -> tuple[Optional[str], Optional[str], float, list[str]]:
    """任务约定的签名：(category_code, category_name, confidence, keywords_hit)。"""
    r = classify_full(text)
    return r["category_code"], r["category_name"], r["confidence"], r["keywords_hit"]


# ---------------------------------------------------------------------------
# 理解
# ---------------------------------------------------------------------------
_TIME_PATTERNS = [
    r"\d{4}年\d{1,2}月\d{1,2}日",
    r"\d{1,2}月\d{1,2}日",
    r"\d{1,2}点\d{0,2}分?",
    r"上[下]午\d{1,2}点",
    r"(?:早上|晚上|凌晨|上午|下午)\d{1,2}点",
    r"上次|近期|此前|近日|多日|几天前|长期|日前",
]
_LOCATION_SUFFIX = (
    r"(?:县|区|镇|乡|街道|路|大道|街|小区|村|广场|站|园区|开发区|新村|花园)"
)
_LOCATION_RE = re.compile(
    r"(?:芜湖市)?[\u4e00-\u9fa5]{1,8}?" + _LOCATION_SUFFIX
)
# 仅含泛化后缀、缺少具体专名的"地点"视为无效（如单独的「小区」「花园」），需澄清
_BARE_LOCATION_WORDS = {"小区", "花园", "新村", "园区"}
_PARTY_RE = re.compile(r"([\u4e00-\u9fa5]{1,4})(先生|女士|女士)")
_DEMAND_RE = re.compile(r"(诉求|要求|希望|恳请|请|反映)([^。；;]*)[。；;]?")


def _extract_time(text: str) -> Optional[str]:
    found = []
    for pat in _TIME_PATTERNS:
        for m in re.finditer(pat, text):
            found.append(m.group(0))
    if not found:
        return None
    # 去重并保持顺序
    seen = []
    for f in found:
        if f not in seen:
            seen.append(f)
    return "、".join(seen[:3])


def _extract_location(text: str) -> Optional[str]:
    # 后缀（县/区/路/小区/花园/...）前必须有非空专名；
    # 若匹配到的只是「小区/花园」这类泛化词（无具体专名），视为无效，继续寻找下一个有效地点。
    for m in _LOCATION_RE.finditer(text):
        loc = m.group(0)
        if loc and loc not in _BARE_LOCATION_WORDS:
            return loc
    return None


def _extract_parties(text: str) -> list[str]:
    parties = []
    for m in _PARTY_RE.finditer(text):
        name = m.group(1) + m.group(2)
        if name not in parties:
            parties.append(name)
    if not parties and "市民" in text:
        parties.append("市民")
    return parties


def _extract_demand(text: str) -> Optional[str]:
    # 优先取 "诉求/要求/希望/恳请/请" 之后的内容
    m = _DEMAND_RE.search(text)
    if m:
        return (m.group(1) + m.group(2)).strip()
    return None


def understand(text: str) -> UnderstandingResult:
    time = _extract_time(text)
    location = _extract_location(text)
    parties = _extract_parties(text)
    demand = _extract_demand(text)

    # 事件：诉求之前的描述性内容
    event: Optional[str] = None
    if demand:
        idx = text.find(demand)
        if idx > 0:
            event = text[:idx].strip("，。；;：: ")
            event = re.sub(r"^(市民|先生|女士|某)?(来电|致电)?(反映|反映：|来电反映|来电反映：)", "", event)
            event = event.strip("，。；;：: ")
        else:
            event = text.replace(demand, "").strip("，。；;：: ")
    else:
        # 无明确诉求标记，取首句
        first = re.split(r"[。；;]", text)[0]
        if len(first) > 4:
            event = first
    if not event:
        event = None

    missing: list[str] = []
    if not location:
        missing.append("地点")
    if not event:
        missing.append("事件")
    if not demand:
        missing.append("诉求")
    needs_clarification = bool(missing)

    urgent = any(w in text for w in URGENT_WORDS)
    repeat_request = any(w in text for w in REPEAT_WORDS)

    return UnderstandingResult(
        transcript=text,
        transcript_source="text",
        time=time,
        location=location,
        parties=parties,
        event=event,
        demand=demand,
        other=None,
        needs_clarification=needs_clarification,
        missing_fields=missing,
        urgent=urgent,
        repeat_request=repeat_request,
        source="local-engine",
    )


# ---------------------------------------------------------------------------
# 工单生成
# ---------------------------------------------------------------------------
def work_order(
    text: str,
    understanding: UnderstandingResult,
    category_name: Optional[str],
) -> WorkOrder:
    who = "、".join(understanding.parties) if understanding.parties else "市民"
    loc = understanding.location or "（地点待补充）"
    cat = category_name or "（待分类）"

    title = f"关于{who}反映{loc}{cat}相关的问题"
    summary = (understanding.demand or understanding.event or text)[:120]
    key_elements = []
    if understanding.time:
        key_elements.append(f"时间：{understanding.time}")
    if understanding.location:
        key_elements.append(f"地点：{understanding.location}")
    if understanding.parties:
        key_elements.append(f"涉及对象：{'、'.join(understanding.parties)}")
    if understanding.event:
        key_elements.append(f"事件：{understanding.event}")
    if understanding.demand:
        key_elements.append(f"诉求：{understanding.demand}")
    if understanding.urgent:
        key_elements.append("紧急程度：紧急/安全相关")
    if understanding.repeat_request:
        key_elements.append("备注：重复反映事项")

    return WorkOrder(
        title=title,
        summary=summary,
        content=text,
        key_elements=key_elements,
        suggested_category=category_name,
        source="local-engine",
    )


# ---------------------------------------------------------------------------
# 回复辅助
# ---------------------------------------------------------------------------
def reply(
    understanding: UnderstandingResult,
    category_name: Optional[str],
    classification: Optional[ClassificationResult],
) -> ReplyResult:
    who = "、".join(understanding.parties) if understanding.parties else "市民"
    loc = understanding.location or "您反映的地点"
    cat = category_name or "相关"

    acceptance_notice = (
        f"您好，{who}。您反映的关于{loc}{cat}的问题我们已经收到，"
        f"正在按流程转交承办单位办理，请您保持电话畅通，我们将及时向您反馈进展。"
    )

    main_dept = "相关主管部门"
    co_depts = ""
    if classification and classification.suggestions:
        s = classification.suggestions[0]
        main_dept = s.main
        if s.co:
            co_depts = "，并商请" + "、".join(s.co) + "协办"
    handling_suggestion = (
        f"建议由{main_dept}{co_depts}牵头核实办理。"
        f"请承办单位在受理后及时联系群众了解详情，现场勘验（如适用），"
        f"依法依规处置并将结果书面反馈热线。{'注意该事项含安全/紧急因素，请优先处置。' if understanding.urgent else ''}"
        f"{'该事项为群众重复反映，请重点核查前期办理情况。' if understanding.repeat_request else ''}"
    )

    pre_reply = (
        f"尊敬的{who}：\n您好！您反映的“{understanding.event or cat}”问题已收悉，"
        f"现将有关情况答复如下：\n经核实，我单位已将该事项转交{main_dept}办理，"
        f"承办单位将与您联系并依法依规处理。感谢您对我们工作的关心和支持！"
    )

    callback_script = (
        f"您好，这里是 12345 政务服务便民热线，给您回访您此前反映的"
        f"（{loc}{cat}）问题。想确认一下承办单位是否与您联系、问题是否得到处理？"
        f"如还有疑问，我们可继续为您跟进。"
    )

    tips = [
        "预回复中涉及的具体部门、时限、政策条款请以承办单位正式答复为准。",
        "若群众提供了姓名/联系方式，注意个人信息保护，答复文本中按需脱敏。",
        "如涉及安全、紧急或重复反映，应在预回复中体现优先处置与前期核查。",
    ]
    if understanding.needs_clarification:
        tips.insert(
            0,
            "群众诉求存在缺失信息（"
            + "、".join(understanding.missing_fields)
            + "），建议先补充核实再正式答复。",
        )

    return ReplyResult(
        acceptance_notice=acceptance_notice,
        handling_suggestion=handling_suggestion,
        pre_reply=pre_reply,
        callback_script=callback_script,
        modification_tips=tips,
        source="local-engine",
    )


def build_department_suggestions(text: str, category_code: Optional[str], category_name: Optional[str]) -> list[DepartmentSuggestion]:
    """依据 department_rules.json 构建承办单位推荐。"""
    rules_doc = loaders.load_department_rules()
    rules = rules_doc.get("rules", [])
    suggestions: list[DepartmentSuggestion] = []
    if not category_code:
        return suggestions
    for rule in rules:
        if rule.get("category_code") != category_code:
            continue
        reason_parts = []
        resp = rule.get("responsibilities", "")
        kws = rule.get("keywords", [])
        reason_parts.append(resp)
        if kws:
            reason_parts.append("匹配关键词：" + "、".join(kws))
        hit = [k for k in kws if k in text]
        if hit:
            reason_parts.append("命中：" + "、".join(hit))
        suggestions.append(
            DepartmentSuggestion(
                main=rule.get("department", "待定"),
                co=rule.get("co_departments", []) or [],
                reason="。".join([p for p in reason_parts if p]),
            )
        )
    return suggestions


def random_historical_content() -> str:
    """从历史事件中随机取一条 request_content（用于模拟转写兜底）。"""
    cases = loaders.load_historical_cases()
    if not cases:
        return "（示例）市民反映小区附近路灯长期不亮，影响夜间出行，请相关部门检修。"
    return random.choice(cases).get("request_content", "")
