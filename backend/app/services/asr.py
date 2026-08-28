"""录音转写：精确匹配样例 > 科大讯飞 ASR > 模拟兜底。

业务契约（与 orchestrator / api 层约定，保持不变）：
    transcribe(filename, uploaded_bytes) -> (transcript, transcript_source)
source 取值：sample-match | kdxf-asr | simulated
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import string
import time
import traceback
from datetime import datetime
from typing import Optional, Tuple
from urllib import error, parse, request

from app.config import settings
from app.data import loaders


def _kdxf_available() -> bool:
    values = (
        settings.KDXF_ASR_APP_ID,
        settings.KDXF_ASR_ACCESS_KEY_ID,
        settings.KDXF_ASR_ACCESS_KEY_SECRET,
    )
    return all(bool(value) and value != "replace_me" for value in values)


def _kdxf_base_url() -> str:
    return (
        settings.KDXF_ASR_BASE_URL or "https://office-api-ist-dx.iflyaisol.com"
    ).rstrip("/")


def _kdxf_datetime() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def _kdxf_signature_random() -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(16))


def _kdxf_signature(params: dict[str, object]) -> str:
    """按 kdxf.md 规则生成 HMAC-SHA1 + Base64 签名。"""
    pairs: list[str] = []
    for key in sorted(params):
        if key == "signature":
            continue
        value = params[key]
        if value is None or value == "":
            continue
        encoded_key = parse.quote_plus(str(key), safe="")
        encoded_value = parse.quote_plus(str(value), safe="")
        pairs.append(f"{encoded_key}={encoded_value}")

    base_string = "&".join(pairs)
    digest = hmac.new(
        settings.KDXF_ASR_ACCESS_KEY_SECRET.encode("utf-8"),
        base_string.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def _kdxf_query(params: dict[str, object]) -> str:
    filtered = {k: str(v) for k, v in params.items() if v is not None and v != ""}
    return parse.urlencode(filtered)


def _kdxf_post_json(url: str, body: bytes, headers: dict[str, str]) -> dict:
    req = request.Request(url, data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"KDXF ASR HTTP {exc.code}: {raw}") from exc
    return json.loads(raw)


def _kdxf_upload(
    filename: Optional[str], audio_bytes: bytes, signature_random: str
) -> tuple[str, int]:
    safe_filename = os.path.basename(filename or "upload.mp3")
    params: dict[str, object] = {
        "appId": settings.KDXF_ASR_APP_ID,
        "accessKeyId": settings.KDXF_ASR_ACCESS_KEY_ID,
        "dateTime": _kdxf_datetime(),
        "signatureRandom": signature_random,
        "fileSize": str(len(audio_bytes)),
        "fileName": safe_filename,
        "durationCheckDisable": "true",
        "language": settings.KDXF_ASR_LANGUAGE or "autodialect",
        "audioMode": "fileStream",
    }
    signature = _kdxf_signature(params)
    url = f"{_kdxf_base_url()}/v2/upload?{_kdxf_query(params)}"
    data = _kdxf_post_json(
        url,
        audio_bytes,
        {
            "Content-Type": "application/octet-stream",
            "signature": signature,
        },
    )
    if str(data.get("code")) != "000000":
        raise RuntimeError(f"KDXF upload failed: {data}")

    content = data.get("content") or {}
    order_id = content.get("orderId")
    if not order_id:
        raise RuntimeError(f"KDXF upload missing orderId: {data}")
    estimate_ms = int(content.get("taskEstimateTime") or 0)
    return str(order_id), estimate_ms


def _kdxf_get_result(order_id: str, signature_random: str) -> dict:
    params: dict[str, object] = {
        "accessKeyId": settings.KDXF_ASR_ACCESS_KEY_ID,
        "dateTime": _kdxf_datetime(),
        "signatureRandom": signature_random,
        "orderId": order_id,
        "resultType": "transfer",
    }
    signature = _kdxf_signature(params)
    url = f"{_kdxf_base_url()}/v2/getResult?{_kdxf_query(params)}"
    return _kdxf_post_json(
        url,
        b"{}",
        {
            "Content-Type": "application/json",
            "signature": signature,
        },
    )


def _parse_kdxf_order_text(order_result: object) -> Optional[str]:
    """解析讯飞 orderResult 中 lattice/json_1best 的转写文本。"""
    if not order_result:
        return None
    if isinstance(order_result, str):
        order_result = json.loads(order_result)
    if not isinstance(order_result, dict):
        return None

    lattice = order_result.get("lattice") or order_result.get("lattice2") or []
    pieces: list[str] = []
    for item in lattice:
        if not isinstance(item, dict):
            continue
        one_best = item.get("json_1best")
        if not one_best:
            continue
        detail = json.loads(one_best) if isinstance(one_best, str) else one_best
        st = (detail or {}).get("st") or {}
        for rt in st.get("rt") or []:
            for ws in rt.get("ws") or []:
                cws = ws.get("cw") or []
                if not cws:
                    continue
                word = cws[0].get("w", "")
                word_type = cws[0].get("wp", "")
                if not word or word_type == "g":
                    continue
                pieces.append(word.replace("｡", "。"))

    text = "".join(pieces).strip()
    return text or None


def _transcribe_kdxf_file_asr(
    filename: Optional[str], audio_bytes: bytes
) -> Optional[str]:
    """调用科大讯飞录音文件转写：上传文件并轮询转写结果。"""
    signature_random = _kdxf_signature_random()
    order_id, estimate_ms = _kdxf_upload(filename, audio_bytes, signature_random)

    poll_interval = max(1, int(settings.KDXF_ASR_POLL_INTERVAL_SECONDS or 5))
    timeout_seconds = max(poll_interval, int(settings.KDXF_ASR_POLL_TIMEOUT_SECONDS or 900))
    deadline = time.monotonic() + timeout_seconds

    if estimate_ms > 0:
        time.sleep(min(max(estimate_ms / 1000.0, 1.0), poll_interval))

    while time.monotonic() < deadline:
        data = _kdxf_get_result(order_id, signature_random)
        if str(data.get("code")) != "000000":
            # 100013 表示订单未完成，按处理中继续轮询。
            if str(data.get("code")) == "100013":
                time.sleep(poll_interval)
                continue
            raise RuntimeError(f"KDXF getResult failed: {data}")

        content = data.get("content") or {}
        order_info = content.get("orderInfo") or {}
        status = int(order_info.get("status") or 0)
        if status == 4:
            return _parse_kdxf_order_text(content.get("orderResult"))
        if status == -1:
            raise RuntimeError(f"KDXF order failed: {data}")
        time.sleep(poll_interval)

    raise TimeoutError(f"KDXF ASR timeout waiting for order {order_id}")


def _source_id_index() -> dict[str, dict]:
    """source_id(去扩展名) -> 历史工单记录。"""
    idx: dict[str, dict] = {}
    for case in loaders.load_historical_cases():
        sid = case.get("source_id", "")
        if sid:
            idx[sid] = case
    return idx


def transcribe(
    filename: Optional[str], uploaded_bytes: Optional[bytes] = None
) -> Tuple[str, str]:
    """返回 (transcript, transcript_source)。"""

    # 1) 精确匹配：官方样例录音保留原名时直接返回预设原文（无需联网）
    if filename:
        base = os.path.splitext(os.path.basename(filename))[0]
        idx = _source_id_index()
        if base in idx:
            return idx[base].get("request_content", ""), "sample-match"

    # 2) 科大讯飞真实 ASR：仅当配置完整且有音频字节时调用
    if _kdxf_available() and uploaded_bytes:
        try:
            text = _transcribe_kdxf_file_asr(filename, uploaded_bytes)
            if text:
                return text, "kdxf-asr"
        except Exception:
            # 任何异常（网络、鉴权、格式）均回退到模拟，保证业务流程不中断
            traceback.print_exc()

    # 3) 模拟兜底：随机返回一条历史工单文本，并明确标注为模拟
    sample = loaders.load_historical_cases()
    content = ""
    if sample:
        import random

        content = random.choice(sample).get("request_content", "")
    return (
        "模拟转写（未配置/未成功调用科大讯飞 ASR，以下为示例文本）\n" + content,
        "simulated",
    )
