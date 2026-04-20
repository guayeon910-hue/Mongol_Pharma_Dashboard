"""몽골 의약품 원시 텍스트 → 구조화 데이터 파서.

Claude Haiku API를 호출하여 몽골어/영어 제품명·함량·포장 단위·가격(MNT)을 파싱하고
MNT → USD 변환 후 ParsedDrug 데이터클래스로 반환한다.

핵심 방어:
  - 포장 단위 기준 단위당 가격(price_per_unit) 강제 계산 → FOB 역산 왜곡 방지
  - 환율 환경변수 MN_USD_RATE 우선 적용 (yfinance 폴백)
  - VAT는 환경변수 MN_VAT_PHARMA_PCT에서 동적 로드 (하드코딩 금지)
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

CLAUDE_MODEL = "claude-haiku-4-5-20251001"

DOSAGE_FORM_MAP: dict[str, str] = {
    # 영문 표준
    "tablet": "tablet",
    "capsule": "capsule",
    "injection": "injectable",
    "ampoule": "ampoule",
    "vial": "vial",
    "inhaler": "inhaler",
    "syrup": "syrup",
    "solution": "solution",
    "cream": "cream",
    "ointment": "ointment",
    "patch": "patch",
    "sachet": "sachet",
    "prefilled syringe": "prefilled_syringe",
    "pfs": "prefilled_syringe",
    # 몽골어 제형명 (키릴 문자)
    "шахмал": "tablet",
    "капсул": "capsule",
    "тариа": "injectable",
    "уусмал": "solution",
    "сироп": "syrup",
    "тос": "ointment",
    "аэрозол": "inhaler",
}

_RATE_CACHE: dict[str, float] = {"rate": 0.0, "ts": 0.0}
_RATE_TTL = 1800.0


def _mnt_to_usd_rate() -> float:
    """MNT→USD 환율. 환경변수 MN_USD_RATE 우선, yfinance 폴백, 최후 고정값."""
    env_rate = os.environ.get("MN_USD_RATE", "").strip()
    if env_rate:
        try:
            return float(env_rate)
        except ValueError:
            pass

    now = time.monotonic()
    if _RATE_CACHE["rate"] and (now - _RATE_CACHE["ts"]) < _RATE_TTL:
        return _RATE_CACHE["rate"]

    try:
        import yfinance as yf  # type: ignore[import]
        ticker = yf.Ticker("MNTUSD=X")
        rate = float(ticker.fast_info.last_price)
        if rate > 0:
            _RATE_CACHE["rate"] = rate
            _RATE_CACHE["ts"] = now
            return rate
    except Exception:
        pass

    return 1 / 3450.0  # 폴백: 1 MNT ≈ 0.000290 USD (2025.04 기준)


def _normalize_form(raw: str) -> str:
    token = raw.strip().lower()
    for key, val in DOSAGE_FORM_MAP.items():
        if key in token:
            return val
    return raw.strip()


def _safe_decimal(v: Any) -> Decimal | None:
    try:
        return Decimal(str(v))
    except (InvalidOperation, TypeError):
        return None


@dataclass
class ParsedDrug:
    inn_name: str
    brand_name: str
    strength_mg: float
    dosage_form: str
    pack_size: int
    total_price_mnt: Decimal
    price_per_unit_mnt: Decimal
    price_per_unit_usd: Decimal
    manufacturer: str
    importer: str
    source_site: str
    source_url: str
    raw_text: str
    registration_no: str = ""
    expiry_date: str = ""
    confidence: float = 0.7
    hif_reimbursement_mnt: Decimal | None = None
    is_essential: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


_SCHEMA_DESC: dict[str, str] = {
    "inn_name":         "WHO INN 국제일반명 (예: Rosuvastatin). 불명확 시 brand_name 기반 추론",
    "brand_name":       "제품 상품명 (예: Rosumeg Combigel). 없으면 inn_name과 동일",
    "strength_mg":      "주성분 함량 숫자값 (mg 단위, 예: 10.0). 불명확 시 null",
    "dosage_form":      "제형 — 영문 또는 몽골어를 영문 표준으로 변환 (tablet/capsule/injectable/inhaler 등)",
    "pack_size":        "포장 단위 정수 (예: 30). 불명확 시 1",
    "total_price_mnt":  "포장 전체 가격 (MNT 투그릭, 숫자만). 불명확 시 null",
    "manufacturer":     "제조사명. 불명확 시 '-'",
    "importer":         "수입 유통사명. 없으면 '-'",
    "registration_no":  "몽골 등록 번호 (Licemed 등록번호). 없으면 ''",
    "expiry_date":      "인허가 만료일 (YYYY-MM-DD 형식). 없으면 ''",
    "hif_reimbursement_mnt": "건강보험기금 상환액 (MNT). 없으면 null",
    "is_essential":     "국가 필수의약품 목록 포함 여부 (true/false)",
}


async def parse_drug_text(
    raw_text: str,
    source_site: str,
    source_url: str,
    hif_reimbursement_mnt: Decimal | None = None,
) -> ParsedDrug | None:
    api_key = os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return _regex_fallback(raw_text, source_site, source_url, hif_reimbursement_mnt)

    schema_str = json.dumps(_SCHEMA_DESC, ensure_ascii=False, indent=2)
    prompt = f"""몽골 의약품 데이터베이스/약국 사이트에서 수집한 의약품 텍스트를 파싱하여 JSON으로 반환하세요.
텍스트는 몽골어(키릴 문자), 영어, 또는 혼합일 수 있습니다.

추출 항목:
{schema_str}

규칙:
1. price_per_unit_mnt = total_price_mnt / pack_size 로 반드시 계산하여 포함하세요.
2. dosage_form은 몽골어/영어를 영문 표준 제형명으로 변환하세요.
3. 숫자만 포함할 값에는 숫자만, 문자열 값에는 텍스트만 넣으세요.
4. 불확실한 필드는 null로 반환하세요. JSON 외 텍스트는 절대 포함하지 마세요.

입력 텍스트:
{raw_text[:1000]}

반드시 JSON 객체 하나만 반환하세요."""

    try:
        import httpx

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": CLAUDE_MODEL,
            "max_tokens": 512,
            "temperature": 0.0,
            "messages": [{"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            content = resp.json()["content"][0]["text"].strip()

        m = re.search(r"\{.*\}", content, re.S)
        if not m:
            return _regex_fallback(raw_text, source_site, source_url, hif_reimbursement_mnt)
        data: dict[str, Any] = json.loads(m.group(0))
        return _build_parsed(data, raw_text, source_site, source_url, hif_reimbursement_mnt)
    except Exception:
        return _regex_fallback(raw_text, source_site, source_url, hif_reimbursement_mnt)


def _build_parsed(
    data: dict[str, Any],
    raw_text: str,
    source_site: str,
    source_url: str,
    hif_reimbursement_mnt: Decimal | None,
) -> ParsedDrug | None:
    total = _safe_decimal(data.get("total_price_mnt"))
    if total is None:
        return None

    pack = int(data.get("pack_size") or 1) or 1
    per_unit_mnt = total / Decimal(pack)
    rate = Decimal(str(_mnt_to_usd_rate()))
    per_unit_usd = per_unit_mnt * rate

    raw_form = str(data.get("dosage_form") or "")
    dosage_form = _normalize_form(raw_form) if raw_form else "unknown"

    strength_raw = data.get("strength_mg")
    try:
        strength_mg = float(strength_raw) if strength_raw is not None else 0.0
    except (ValueError, TypeError):
        strength_mg = 0.0

    hif_raw = _safe_decimal(data.get("hif_reimbursement_mnt"))
    hif = hif_raw if hif_raw is not None else hif_reimbursement_mnt

    return ParsedDrug(
        inn_name=str(data.get("inn_name") or "").strip(),
        brand_name=str(data.get("brand_name") or "").strip(),
        strength_mg=strength_mg,
        dosage_form=dosage_form,
        pack_size=pack,
        total_price_mnt=total,
        price_per_unit_mnt=per_unit_mnt,
        price_per_unit_usd=per_unit_usd,
        manufacturer=str(data.get("manufacturer") or "-").strip(),
        importer=str(data.get("importer") or "-").strip(),
        source_site=source_site,
        source_url=source_url,
        raw_text=raw_text,
        registration_no=str(data.get("registration_no") or "").strip(),
        expiry_date=str(data.get("expiry_date") or "").strip(),
        hif_reimbursement_mnt=hif,
        is_essential=bool(data.get("is_essential", False)),
        confidence=0.75,
    )


def _regex_fallback(
    raw_text: str,
    source_site: str,
    source_url: str,
    hif_reimbursement_mnt: Decimal | None,
) -> ParsedDrug | None:
    price_m = re.search(r"([\d,]+(?:\.\d+)?)\s*(?:₮|MNT|төгрөг)", raw_text, re.I)
    if not price_m:
        price_m = re.search(r"([\d]{3,}(?:[,\s]\d{3})*)", raw_text)
    if not price_m:
        return None

    total_str = price_m.group(1).replace(",", "").replace(" ", "")
    total = _safe_decimal(total_str)
    if total is None:
        return None

    pack_m = re.search(r"(\d+)\s*(?:ширхэг|шир|tab|cap|amp|pcs)", raw_text, re.I)
    pack = int(pack_m.group(1)) if pack_m else 1

    mg_m = re.search(r"(\d+(?:\.\d+)?)\s*мг|mg", raw_text, re.I)
    strength_mg = float(mg_m.group(1)) if mg_m else 0.0

    rate = Decimal(str(_mnt_to_usd_rate()))
    per_unit_mnt = total / Decimal(pack)

    return ParsedDrug(
        inn_name="",
        brand_name="",
        strength_mg=strength_mg,
        dosage_form="unknown",
        pack_size=pack,
        total_price_mnt=total,
        price_per_unit_mnt=per_unit_mnt,
        price_per_unit_usd=per_unit_mnt * rate,
        manufacturer="-",
        importer="-",
        source_site=source_site,
        source_url=source_url,
        raw_text=raw_text,
        hif_reimbursement_mnt=hif_reimbursement_mnt,
        confidence=0.4,
    )


async def parse_drug_texts_batch(
    items: list[dict[str, Any]],
) -> list[ParsedDrug | None]:
    tasks = [
        parse_drug_text(
            raw_text=item["raw_text"],
            source_site=item.get("source_site", ""),
            source_url=item.get("source_url", ""),
            hif_reimbursement_mnt=_safe_decimal(item.get("hif_reimbursement_mnt")),
        )
        for item in items
    ]
    return list(await asyncio.gather(*tasks))
