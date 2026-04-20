"""몽골(MN) 의약품 시장 분석 오케스트레이터 (3계층 통합).

주요 흐름:
  1. Tier 1 — MMRA 규제 공시 + Licemed 등록 DB 크롤링
  2. Tier 2 — EMD 약가 고시 + tender.gov.mn 공공 조달 입찰 크롤링
  3. Tier 3 — 유통사 포트폴리오 크롤링 + 파트너 점수 산출
  4. mn_parser.py로 몽골어 텍스트 파싱 및 MNT→USD 변환
  5. Supabase mn_pricing 테이블에 INSERT
  6. FOB 역산기 실행 → 3 시나리오 반환
  7. 경쟁 분석: 만료 임박 제품·독점 성분·파트너 랭킹

자사 8품목:
  Rosumeg Combigel (Rosuvastatin+Omega-3)
  Atmeg Combigel   (Atorvastatin+Omega-3)
  Ciloduo          (Cilostazol+Rosuvastatin)
  Omethyl Cutielet (Omega-3 고용량)
  Hydrine          (Hydroxyurea 500mg)
  Sereterol Activair (Fluticasone+Salmeterol)
  Gastiin CR       (Mosapride Citrate)
  Gadvoa Inj.      (Gadobutrol)
"""

from __future__ import annotations

import asyncio
import time
from decimal import Decimal
from typing import Any

DEFAULT_INN_NAMES: list[str] = [
    "Rosuvastatin",
    "Atorvastatin",
    "Cilostazol",
    "Omega-3",
    "Gadobutrol",
    "Hydroxyurea",
    "Fluticasone",
    "Salmeterol",
    "Mosapride",
]

OUTLIER_THRESHOLD = 0.35


# ── Tier 1: 규제·인허가 ──────────────────────────────────────────────────────

async def run_tier1_regulatory(
    emit: Any = None,
) -> dict[str, Any]:
    from utils.mn_mmra_crawler import crawl_mmra_notices, filter_by_target_inns
    from utils.mn_licemed_crawler import crawl_all_inns, analyze_competition

    if emit:
        await emit({"phase": "tier1", "message": "MMRA 규제 공시 수집 시작", "level": "info"})

    notices = await crawl_mmra_notices(emit=emit)
    relevant_notices = filter_by_target_inns(notices, DEFAULT_INN_NAMES)

    if emit:
        await emit({"phase": "tier1", "message": "Licemed 등록 DB 크롤링 시작", "level": "info"})

    licemed_data = await crawl_all_inns(emit=emit)
    competition = analyze_competition(licemed_data)

    return {
        "mmra_notices": relevant_notices,
        "licemed_data": licemed_data,
        "competition_analysis": competition,
    }


# ── Tier 2: 약가·공공조달 ───────────────────────────────────────────────────

async def run_tier2_pricing(
    emit: Any = None,
) -> dict[str, Any]:
    from utils.mn_emd_crawler import crawl_emd_pricing, crawl_contracted_pharmacies, match_to_products
    from utils.mn_tender_crawler import crawl_all_targets, rank_vendors

    if emit:
        await emit({"phase": "tier2", "message": "EMD 약가 고시 수집 시작", "level": "info"})

    pricing_rows, pharmacy_rows = await asyncio.gather(
        crawl_emd_pricing(),
        crawl_contracted_pharmacies(),
    )

    matched_pricing = match_to_products(pricing_rows, DEFAULT_INN_NAMES)

    if emit:
        await emit({
            "phase": "tier2",
            "message": f"EMD {len(pricing_rows)}건 약가, 약국 {len(pharmacy_rows)}개 수집",
            "level": "success",
        })
        await emit({"phase": "tier2", "message": "tender.gov.mn 입찰 수집 시작", "level": "info"})

    tender_data = await crawl_all_targets(emit=emit)
    vendor_ranking = rank_vendors(tender_data)

    return {
        "pricing_rows": pricing_rows,
        "matched_pricing": matched_pricing,
        "pharmacy_distribution": pharmacy_rows,
        "tender_data": tender_data,
        "vendor_ranking": vendor_ranking,
    }


# ── Tier 3: 유통사 매핑 ────────────────────────────────────────────────────

async def run_tier3_distributors(
    vendor_ranking: list[dict[str, Any]] | None = None,
    emit: Any = None,
) -> dict[str, Any]:
    from utils.mn_distributor_crawler import (
        crawl_all_distributors,
        find_whitespace,
        score_partners,
    )

    if emit:
        await emit({"phase": "tier3", "message": "유통사 포트폴리오 크롤링 시작", "level": "info"})

    distributor_data = await crawl_all_distributors(emit=emit)
    whitespace = find_whitespace(distributor_data)
    partner_scores = score_partners(distributor_data, tender_ranking=vendor_ranking)

    return {
        "distributor_data": distributor_data,
        "whitespace": whitespace,
        "partner_scores": partner_scores,
    }


# ── FOB 역산 ────────────────────────────────────────────────────────────────

async def run_fob_calculation(
    pricing_matched: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    from analysis.fob_calculator import calc_logic_a, calc_logic_b, fob_result_to_dict
    from utils.mn_macro import get_mnt_to_usd_rate

    rate = get_mnt_to_usd_rate()
    fob_by_inn: dict[str, list[dict[str, Any]]] = {}

    for inn, rows in pricing_matched.items():
        fob_results: list[dict[str, Any]] = []

        public_rows = [r for r in rows if r.get("source_site", "").endswith("pricing")]
        private_rows = [r for r in rows if r not in public_rows]

        def _avg_usd(row_list: list[dict[str, Any]]) -> Decimal | None:
            prices = []
            for r in row_list:
                mnt = r.get("price_mnt")
                if mnt and float(mnt) > 0:
                    prices.append(float(mnt) * rate)
            if not prices:
                return None
            return Decimal(str(sum(prices) / len(prices)))

        avg_pub = _avg_usd(public_rows)
        if avg_pub:
            result_a = calc_logic_a(avg_pub, inn_name=inn)
            fob_results.append({**fob_result_to_dict(result_a), "source_count": len(public_rows)})

        avg_priv = _avg_usd(private_rows)
        if avg_priv:
            result_b = calc_logic_b(avg_priv, inn_name=inn)
            fob_results.append({**fob_result_to_dict(result_b), "source_count": len(private_rows)})

        fob_by_inn[inn] = fob_results

    return fob_by_inn


# ── Supabase 저장 ───────────────────────────────────────────────────────────

def _build_db_row(
    inn: str,
    row: dict[str, Any],
) -> dict[str, Any]:
    from utils.mn_macro import get_mnt_to_usd_rate
    rate = get_mnt_to_usd_rate()

    mnt_price = float(row.get("price_mnt", 0) or 0)
    usd_price = mnt_price * rate if mnt_price > 0 else None

    return {
        "inn_name": inn,
        "drug_name": row.get("drug_name", ""),
        "source_site": row.get("source_site", ""),
        "source_url": row.get("source_url", ""),
        "price_mnt": mnt_price,
        "price_usd": usd_price,
        "hif_reimbursement_mnt": row.get("hif_reimbursement_mnt"),
        "copayment_mnt": row.get("copayment_mnt"),
        "manufacturer": row.get("manufacturer", ""),
        "importer": row.get("importer", ""),
        "registration_no": row.get("registration_no", ""),
        "expiry_date": row.get("expiry_date"),
        "is_essential": row.get("is_essential", False),
        "file_url": row.get("file_url", ""),
        "confidence": 0.8,
    }


async def save_to_supabase(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    try:
        from utils.db import get_supabase_client
        sb = get_supabase_client()
        result = sb.table("mn_pricing").insert(rows).execute()
        return len(result.data) if result.data else 0
    except Exception:
        return 0


# ── 메인 오케스트레이터 ────────────────────────────────────────────────────

async def analyze_mn_market(
    inn_names: list[str] | None = None,
    save_db: bool = True,
    run_tiers: list[int] | None = None,
    emit: Any = None,
) -> dict[str, Any]:
    """몽골 시장 전체 분석 실행.

    Args:
        inn_names: 분석 대상 INN 목록 (None 시 8품목 전체)
        save_db: Supabase 저장 여부
        run_tiers: 실행할 계층 목록 (None 시 전체 [1,2,3])
        emit: SSE 이벤트 콜백
    """
    start = time.time()
    tiers = run_tiers or [1, 2, 3]

    tier1_result: dict[str, Any] = {}
    tier2_result: dict[str, Any] = {}
    tier3_result: dict[str, Any] = {}

    if 1 in tiers:
        tier1_result = await run_tier1_regulatory(emit=emit)

    if 2 in tiers:
        tier2_result = await run_tier2_pricing(emit=emit)

    vendor_ranking = tier2_result.get("vendor_ranking")
    if 3 in tiers:
        tier3_result = await run_tier3_distributors(vendor_ranking=vendor_ranking, emit=emit)

    fob_results: dict[str, Any] = {}
    matched_pricing = tier2_result.get("matched_pricing", {})
    if matched_pricing:
        fob_results = await run_fob_calculation(matched_pricing)

    all_db_rows: list[dict[str, Any]] = []
    for inn, rows in matched_pricing.items():
        for row in rows:
            all_db_rows.append(_build_db_row(inn, row))

    saved_count = 0
    if save_db and all_db_rows:
        saved_count = await save_to_supabase(all_db_rows)
        if emit:
            await emit({
                "phase": "db",
                "message": f"Supabase mn_pricing {saved_count}건 적재 완료",
                "level": "success",
            })

    elapsed = round(time.time() - start, 1)

    return {
        "ok": True,
        "elapsed_sec": elapsed,
        "inn_names": inn_names or DEFAULT_INN_NAMES,
        "saved_to_db": saved_count,
        "tier1": tier1_result,
        "tier2": {
            "pricing_count": len(tier2_result.get("pricing_rows", [])),
            "pharmacy_count": len(tier2_result.get("pharmacy_distribution", [])),
            "vendor_ranking": vendor_ranking or [],
            "matched_pricing": {
                inn: len(rows) for inn, rows in matched_pricing.items()
            },
        },
        "tier3": {
            "whitespace": tier3_result.get("whitespace", {}),
            "partner_scores": tier3_result.get("partner_scores", []),
        },
        "fob_results": fob_results,
    }
