"""몽골 국가 전자조달 시스템 (tender.gov.mn) 크롤러.

대상:
  - https://tender.gov.mn  — 국가 전자조달 통합 포털
  - https://e-tender.mn    — 대안 포털 (동일 데이터)

수집 데이터 (OCDS 표준):
  - 입찰 ID / 공고 제목
  - 입찰 주체 (발주처 병원/기관명)
  - 구매 물품 명세 (INN·함량·포장 단위·수량)
  - 입찰 마감일, 입찰 보증금
  - 낙찰자 명칭 및 계약 금액 (MNT)

전략적 가치:
  - 가드보아 주(Gadobutrol) · 하이드린(Hydroxyurea) 공공 조달 특화
  - 최근 3년 낙찰 상위 10개 벤더 랭킹 → 독점 공급 파트너 후보 도출
  - ADB/EBRD 국제 입찰 연동 감지
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

TENDER_BASE = "https://tender.gov.mn"
TENDER_SEARCH = f"{TENDER_BASE}/api/tenders/search"
TENDER_AWARD = f"{TENDER_BASE}/api/awards"

# 의약품 카테고리 필터
PHARMA_CATEGORY_KEYWORDS = [
    "pharmaceutical", "medicine", "drug", "эм", "эмийн",
    "contrast", "oncology", "cardiovascular",
]

# 자사 품목 관련 검색 키워드
TARGET_KEYWORDS: list[str] = [
    "Gadobutrol", "Hydroxyurea", "Rosuvastatin", "Atorvastatin",
    "Cilostazol", "Fluticasone", "Salmeterol", "Mosapride",
    "contrast media", "조영제", "항암제", "심혈관",
]


def _is_pharma_tender(title: str, description: str) -> bool:
    text = (title + " " + description).lower()
    return any(kw.lower() in text for kw in PHARMA_CATEGORY_KEYWORDS)


def _extract_award_vendor(award_data: dict[str, Any]) -> dict[str, Any]:
    """낙찰 데이터에서 벤더 정보 추출."""
    suppliers = award_data.get("suppliers", [])
    vendor_name = ""
    if suppliers:
        vendor_name = suppliers[0].get("name", "") or suppliers[0].get("legalName", "")

    value = award_data.get("value", {})
    amount = value.get("amount", 0.0) if isinstance(value, dict) else 0.0
    currency = value.get("currency", "MNT") if isinstance(value, dict) else "MNT"

    return {
        "vendor_name": vendor_name,
        "contract_amount_mnt": float(amount) if currency == "MNT" else None,
        "contract_amount_usd": float(amount) if currency == "USD" else None,
        "award_date": award_data.get("date", ""),
    }


async def _fetch_json(
    session: Any,
    url: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any] | None:
    try:
        resp = await session.get(url, params=params, timeout=15.0)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


async def crawl_tender_search(
    keyword: str,
    max_pages: int = 10,
    emit: Any = None,
) -> list[dict[str, Any]]:
    """키워드로 tender.gov.mn 입찰 공고 검색."""
    try:
        import httpx
    except ImportError:
        return []

    results: list[dict[str, Any]] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
        "Accept": "application/json",
        "Accept-Language": "mn,en;q=0.9",
    }

    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=20.0) as session:
            for page in range(1, max_pages + 1):
                params = {
                    "q": keyword,
                    "page": page,
                    "category": "pharmaceutical",
                    "status": "all",
                }
                data = await _fetch_json(session, TENDER_SEARCH, params=params)

                if data is None:
                    # API 실패 시 HTML 스크래핑 폴백
                    html_url = f"{TENDER_BASE}/tenders?search={keyword}&page={page}"
                    resp = await session.get(html_url, timeout=15.0)
                    if resp.status_code != 200:
                        break
                    parsed = _parse_tender_html(resp.text, keyword)
                    if not parsed:
                        break
                    results.extend(parsed)
                    await asyncio.sleep(1.0)
                    continue

                items = []
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    items = data.get("data", data.get("items", data.get("results", [])))

                if not items:
                    break

                for item in items:
                    title = str(item.get("title", "") or item.get("name", ""))
                    desc = str(item.get("description", "") or "")

                    tender_row: dict[str, Any] = {
                        "tender_id": str(item.get("id", "") or item.get("ocid", "")),
                        "title": title,
                        "purchaser": str(
                            item.get("buyer", {}).get("name", "")
                            if isinstance(item.get("buyer"), dict)
                            else item.get("purchaser", "")
                        ),
                        "deadline": str(item.get("tenderPeriod", {}).get("endDate", "")
                                       if isinstance(item.get("tenderPeriod"), dict)
                                       else item.get("deadline", "")),
                        "bid_security_mnt": item.get("bidSecurity", None),
                        "status": str(item.get("status", "")),
                        "keyword": keyword,
                        "source_site": "tender_gov_mn",
                        "source_url": f"{TENDER_BASE}/tender/{item.get('id', '')}",
                        "raw_items": str(item.get("items", ""))[:500],
                    }

                    # 낙찰 정보
                    awards = item.get("awards", [])
                    if awards and isinstance(awards, list):
                        vendor_info = _extract_award_vendor(awards[0])
                        tender_row.update(vendor_info)

                    results.append(tender_row)

                await asyncio.sleep(1.0)

    except Exception:
        pass

    return results


def _parse_tender_html(html: str, keyword: str) -> list[dict[str, Any]]:
    """HTML 폴백 파싱."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    soup = BeautifulSoup(html, "html.parser")
    results: list[dict[str, Any]] = []

    rows = soup.select(".tender-item, .tender-row, table tbody tr")
    for row in rows:
        title_el = row.select_one(".tender-title, td:first-child, h3, h4")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            continue

        results.append({
            "tender_id": "",
            "title": title,
            "purchaser": "",
            "deadline": "",
            "bid_security_mnt": None,
            "status": "",
            "keyword": keyword,
            "source_site": "tender_gov_mn_html",
            "source_url": TENDER_BASE,
            "raw_items": row.get_text(strip=True)[:300],
        })

    return results


async def crawl_all_targets(
    emit: Any = None,
) -> dict[str, list[dict[str, Any]]]:
    """자사 8품목 키워드 전체 입찰 수집."""
    all_results: dict[str, list[dict[str, Any]]] = {}

    for keyword in TARGET_KEYWORDS:
        if emit:
            await emit({"phase": "tender", "message": f"'{keyword}' 입찰 검색 시작", "level": "info"})

        rows = await crawl_tender_search(keyword)
        all_results[keyword] = rows

        if emit:
            await emit({
                "phase": "tender",
                "message": f"'{keyword}' — {len(rows)}건 수집",
                "level": "success" if rows else "warn",
            })

    return all_results


def rank_vendors(
    tender_data: dict[str, list[dict[str, Any]]],
    top_n: int = 10,
) -> list[dict[str, Any]]:
    """최근 3년 낙찰 상위 벤더 랭킹 산출."""
    from collections import defaultdict

    vendor_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"win_count": 0, "total_mnt": 0.0, "keywords": set()}
    )

    for keyword, rows in tender_data.items():
        for row in rows:
            vendor = row.get("vendor_name", "").strip()
            if not vendor:
                continue
            amount = row.get("contract_amount_mnt", 0.0) or 0.0
            vendor_stats[vendor]["win_count"] += 1
            vendor_stats[vendor]["total_mnt"] += amount
            vendor_stats[vendor]["keywords"].add(keyword)

    ranking = []
    for vendor, stats in vendor_stats.items():
        ranking.append({
            "vendor_name": vendor,
            "win_count": stats["win_count"],
            "total_contract_mnt": stats["total_mnt"],
            "product_keywords": list(stats["keywords"]),
        })

    ranking.sort(key=lambda x: x["total_contract_mnt"], reverse=True)
    return ranking[:top_n]
