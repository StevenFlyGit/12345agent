"""业务流程编排：串联 ASR → 理解 → 分类 → 工单 → 回复 → 确认。

所有阶段以 case_id 串联，并持久化到 SQLite（store）。每步更新后回写库，
保证任意阶段可独立调用、可断点续跑。
"""
from __future__ import annotations

import random
import string
from datetime import datetime

from app.config import get_workflow_engine
from app.graph.workflow import run_case_graph
from app.schemas.models import (
    CaseInput,
    CaseState,
    ClassificationResult,
    ReplyResult,
    WorkOrder,
)
from app.services import asr, classify as classify_svc, reply as reply_svc
from app.services import understand as understand_svc
from app.services import workorder as workorder_svc
from app.workflow import store


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _new_case_id() -> str:
    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"wo_{ts}_{rand}"


def _use_langgraph() -> bool:
    return get_workflow_engine() == "langgraph"


def _run_graph(case: CaseState, target_stage: str) -> CaseState:
    return run_case_graph(case, target_stage=target_stage)


def create_case(
    text: str | None = None,
    audio_filename: str | None = None,
    audio_bytes: bytes | None = None,
) -> CaseState:
    if _use_langgraph():
        case = CaseState(
            case_id=_new_case_id(),
            created_at=_now(),
            input=CaseInput(text=text, audio_filename=audio_filename),
            audit_log=[{"action": "create", "at": _now(), "workflow": "langgraph"}],
        )

        # 二进制音频不写入 checkpoint；先完成转写，再把纯文本交给图。
        transcript = None
        transcript_source = None
        if not (text and text.strip()) and audio_bytes is not None:
            transcript, transcript_source = asr.transcribe(audio_filename, audio_bytes)

        return run_case_graph(
            case,
            target_stage="understand",
            transcript=transcript,
            transcript_source=transcript_source,
        )

    # 1) 取得转写文本
    if text and text.strip():
        transcript = text
        transcript_source = "text"
    else:
        transcript, transcript_source = asr.transcribe(audio_filename, audio_bytes)

    # 2) 诉求理解
    understanding = understand_svc.understand(transcript, transcript_source)

    case = CaseState(
        case_id=_new_case_id(),
        created_at=_now(),
        input=CaseInput(text=text, audio_filename=audio_filename),
        understanding=understanding,
        audit_log=[{"action": "create", "at": _now()}],
    )
    store.save(case)
    return case


def _require_case(case_id: str) -> CaseState:
    case = store.get(case_id)
    if case is None:
        raise ValueError(f"case_id 不存在: {case_id}")
    return case


def run_understand(case_id: str) -> CaseState:
    """在已建案件上重新执行理解（用于文本回填后再理解）。"""
    case = _require_case(case_id)
    if not case.understanding:
        raise ValueError("案件无转录文本，无法理解")
    if _use_langgraph():
        return _run_graph(case, "understand")
    case.understanding = understand_svc.understand(
        case.understanding.transcript, case.understanding.transcript_source
    )
    case.audit_log.append({"action": "understand", "at": _now()})
    store.save(case)
    return case


def run_classify(case_id: str) -> ClassificationResult:
    case = _require_case(case_id)
    if not case.understanding:
        raise ValueError("请先完成诉求理解")
    if _use_langgraph():
        result_case = _run_graph(case, "classify")
        if result_case.classification is None:
            raise ValueError("分类节点未返回结果")
        return result_case.classification
    text = case.understanding.transcript
    result = classify_svc.classify(text, case.understanding)
    case.classification = result
    case.audit_log.append({"action": "classify", "at": _now()})
    store.save(case)
    return result


def run_workorder(case_id: str) -> WorkOrder:
    case = _require_case(case_id)
    if not case.understanding:
        raise ValueError("请先完成诉求理解")
    if _use_langgraph():
        result_case = _run_graph(case, "workorder")
        if result_case.work_order is None:
            raise ValueError("工单节点未返回结果")
        return result_case.work_order
    text = case.understanding.transcript
    classification = case.classification
    if classification is None:
        # 工单阶段可能早于分类：快速推导建议类别用于填充 suggested_category
        cf = classify_svc.classify(text, case.understanding)
        classification = cf
    result = workorder_svc.generate_work_order(text, case.understanding, classification)
    case.work_order = result
    case.audit_log.append({"action": "workorder", "at": _now()})
    store.save(case)
    return result


def run_reply(case_id: str) -> ReplyResult:
    case = _require_case(case_id)
    if not case.understanding:
        raise ValueError("请先完成诉求理解")
    if _use_langgraph():
        result_case = _run_graph(case, "reply")
        if result_case.reply is None:
            raise ValueError("回复节点未返回结果")
        return result_case.reply
    result = reply_svc.generate_reply(case.understanding, case.classification)
    case.reply = result
    case.audit_log.append({"action": "reply", "at": _now()})
    store.save(case)
    return result


def run_full_workflow(case_id: str) -> CaseState:
    """供教学演示或内部调用，一次执行至质量检查 / 人工复核节点。"""
    case = _require_case(case_id)
    if not case.understanding:
        raise ValueError("请先完成诉求理解")
    if not _use_langgraph():
        raise ValueError("完整图流程仅在 WORKFLOW_ENGINE=langgraph 时可用")
    return _run_graph(case, "full")


def confirm(case_id: str, operator: str, note: str | None = None) -> CaseState:
    case = _require_case(case_id)
    case.confirmed = True
    case.next_action = "confirmed"
    case.audit_log.append(
        {
            "action": "confirm",
            "operator": operator,
            "note": note or "",
            "at": _now(),
        }
    )
    store.save(case)
    return case


def record_handling(case_id: str, text: str) -> CaseState:
    case = _require_case(case_id)
    case.audit_log.append(
        {"action": "handling", "text": text, "at": _now()}
    )
    store.save(case)
    return case
