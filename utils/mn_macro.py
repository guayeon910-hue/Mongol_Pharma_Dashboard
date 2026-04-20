"""몽골(MN) 거시 경제 및 의약품 시장 지표.

수치 출처:
  GDP/capita: IMF World Economic Outlook 2024
  인구: UN World Population Prospects 2024
  의약품 시장: IQVIA / 현지 보건부 추정 (수입의존도 74.2%)
  성장률: IMF 실질 GDP 성장률 2024
  보건지출: WHO GHED 2022
  약가·세금: MMRA / EMD 몽골 보건의료보험청 2025
"""

from __future__ import annotations

import os
import time
from typing import Any

MN_MACRO: dict[str, Any] = {
    "country": "MN",
    "country_name": "몽골",
    "currency": "MNT",
    "gdp_per_capita_usd": 4_200,
    "population_m": 3.4,
    "pharma_market_usd_m": 150,
    "import_share_pct": 74.2,
    "real_growth_pct": 5.0,
    "healthcare_pct_gdp": 4.8,
    "vat_pharma_pct": float(os.environ.get("MN_VAT_PHARMA_PCT", "10.0")),
    "import_duty_pharma_pct": float(os.environ.get("MN_IMPORT_DUTY_PCT", "5.0")),
    "local_wholesale_margin_pct": 5.0,
    "import_wholesale_margin_max_pct": 100.0,
    "essential_medicines_count": 590,
    "pharmacy_facilities": 2822,
    "source": {
        "gdp": "IMF WEO 2024",
        "population": "UN WPP 2024",
        "pharma_market": "IQVIA / 몽골 보건부 추정 2024",
        "import_share": "몽골 보건부 통계 2021",
        "growth": "IMF 실질 GDP 2024",
        "healthcare": "WHO GHED 2022",
        "tax": "MMRA / EMD 몽골 2025",
    },
}

# 대시보드 카드용 정적 폴백
_STATIC_MACRO_CARDS: list[dict] = [
    {"label": "1인당 GDP",      "value": "$4,200",     "sub": "2024  ·  IMF WEO"},
    {"label": "인구",           "value": "340만 명",    "sub": "2024  ·  UN WPP"},
    {"label": "의약품 시장",    "value": "$1.5억",      "sub": "2024  ·  추정 (수입 74.2%)"},
    {"label": "실질 성장률",    "value": "5.0%",        "sub": "2024  ·  IMF"},
]

_cache: list[dict] | None = None
_RATE_CACHE: dict[str, float] = {"rate": 0.0, "ts": 0.0}
_RATE_TTL = 1800.0


def get_mnt_to_usd_rate() -> float:
    """MNT→USD 환율. 환경변수 MN_USD_RATE 우선, 폴백 3450."""
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


def get_mn_macro() -> dict[str, Any]:
    """몽골 거시지표 반환. 환경변수로 VAT·관세 동적 갱신."""
    data = dict(MN_MACRO)
    data["vat_pharma_pct"] = float(os.environ.get("MN_VAT_PHARMA_PCT", "10.0"))
    data["import_duty_pharma_pct"] = float(os.environ.get("MN_IMPORT_DUTY_PCT", "5.0"))
    data["mnt_to_usd_rate"] = get_mnt_to_usd_rate()
    return data


def get_mn_macro_cards() -> list[dict[str, Any]]:
    """대시보드용 카드 배열. Supabase 조회 실패 시 정적 폴백."""
    global _cache
    if _cache is not None:
        return _cache

    try:
        from utils.db import get_supabase_client
        sb = get_supabase_client()
        pop_row = (
            sb.table("mn_world_population")
            .select("population,year")
            .eq("country_code", "MNG")
            .order("year", desc=True)
            .limit(1)
            .execute()
            .data
        )
        result = list(_STATIC_MACRO_CARDS)
        if pop_row:
            p = pop_row[0]
            result[1] = {"label": "인구", "value": f"{p['population']:,}명", "sub": f"{p['year']}  ·  World Bank"}
        _cache = result
        return result
    except Exception:
        return _STATIC_MACRO_CARDS


# 하위 호환 — server.py에서 from utils.mn_macro import MN_MACRO 사용
MN_MACRO_CARDS = _STATIC_MACRO_CARDS
