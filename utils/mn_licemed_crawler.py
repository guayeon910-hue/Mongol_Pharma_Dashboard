"""몽골 국가의약품 통합 등록 시스템 (Licemed) 크롤러.

대상: https://licemed.mohs.mn
수집 데이터:
  - 의약품 명칭 (몽골어/영어)
  - INN 성분명, 제형, 함량
  - 등록 번호 및 인허가 만료일
  - 제조사 및 수입 유통사
  - SPC (Summary of Product Characteristics) 요약
  - 국가 필수의약품 목록 포함 여부

전략적 가치:
  - 경쟁 의약품 만료일 임박 감지 → 시장 공백 선점 타이밍
  - 동일 성분 등재 제조사 수 < 3 → 패스트트랙 인허가 우선권 식별
  - 복합제 동일 성분 단일제 경쟁사 매핑
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

BASE_URL = "https://licemed.mohs.mn"
SEARCH_ENDPOINT = f"{BASE_URL}/medicine/search"

# 자사 8품목 INN 검색어 목록
TARGET_INNS: list[str] = [
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


async def _fetch_search_page(
    session: Any,
    inn: str,
    page: int = 1,
) -> str:
    """Licemed 검색 결과 HTML 반환."""
    params = {"q": inn, "page": page, "type": "import"}
    try:
        resp = await session.get(SEARCH_ENDPOINT, params=params, timeout=15.0)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return ""


def _parse_licemed_html(html: str, inn: str) -> list[dict[str, Any]]:
    """Licemed HTML에서 의약품 메타데이터 추출."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    results: list[dict[str, Any]] = []

    rows = soup.select("table tbody tr, .medicine-item, .drug-row")
    if not rows:
        rows = soup.select("tr")

    for row in rows:
        cells = row.find_all(["td", "th"])
        if len(cells) < 3:
            continue

        text_cells = [c.get_text(strip=True) for c in cells]

        reg_no = ""
        expiry = ""
        manufacturer = ""
        importer = ""
        brand = ""
        form = ""
        strength = ""

        # 등록번호 패턴 (MN-XXXX-XXXX)
        full_text = " ".join(text_cells)
        reg_m = re.search(r"MN[-\s]?\d{4}[-\s]?\d{4}", full_text, re.I)
        if reg_m:
            reg_no = reg_m.group(0)

        # 만료일 패턴
        date_m = re.search(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})", full_text)
        if date_m:
            expiry = f"{date_m.group(1)}-{date_m.group(2).zfill(2)}-{date_m.group(3).zfill(2)}"

        # 함량 패턴
        mg_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:mg|мг)", full_text, re.I)
        if mg_m:
            strength = mg_m.group(0)

        # 셀별 할당 (사이트 구조에 따라 조정 필요)
        if text_cells:
            brand = text_cells[0]
        if len(text_cells) > 1:
            form = text_cells[1]
        if len(text_cells) > 2:
            manufacturer = text_cells[2]
        if len(text_cells) > 3:
            importer = text_cells[3]

        if not brand and not reg_no:
            continue

        results.append({
            "inn_name": inn,
            "brand_name": brand,
            "dosage_form": form,
            "strength": strength,
            "registration_no": reg_no,
            "expiry_date": expiry,
            "manufacturer": manufacturer,
            "importer": importer,
            "source_site": "licemed",
            "source_url": SEARCH_ENDPOINT,
            "raw_text": full_text[:500],
        })

    return results


async def crawl_licemed(
    inn: str,
    max_pages: int = 5,
) -> list[dict[str, Any]]:
    """단일 INN 성분에 대한 Licemed 등록 의약품 목록 수집."""
    try:
        import httpx
    except ImportError:
        return []

    all_results: list[dict[str, Any]] = []

    try:
        async with httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
                "Accept-Language": "mn,en;q=0.9",
            },
            follow_redirects=True,
            timeout=20.0,
        ) as session:
            for page in range(1, max_pages + 1):
                html = await _fetch_search_page(session, inn, page)
                if not html:
                    break
                parsed = _parse_licemed_html(html, inn)
                if not parsed:
                    break
                all_results.extend(parsed)
                await asyncio.sleep(1.5)  # rate limit
    except Exception:
        pass

    return all_results


async def crawl_all_inns(
    inn_list: list[str] | None = None,
    emit: Any = None,
) -> dict[str, list[dict[str, Any]]]:
    """8품목 INN 전체 Licemed 크롤링. 병렬 실행."""
    targets = inn_list or TARGET_INNS
    results: dict[str, list[dict[str, Any]]] = {}

    for inn in targets:
        if emit:
            await emit({"phase": "licemed", "message": f"{inn} — Licemed 조회 시작", "level": "info"})
        data = await crawl_licemed(inn)
        results[inn] = data
        if emit:
            await emit({
                "phase": "licemed",
                "message": f"{inn} — {len(data)}건 수집",
                "level": "success" if data else "warn",
            })

    return results


def analyze_competition(
    licemed_data: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """경쟁 분석: 만료 임박 제품, 독점 성분, 복합제 공백 식별."""
    import datetime

    today = datetime.date.today()
    two_months_later = today + datetime.timedelta(days=60)

    expiring_soon: list[dict[str, Any]] = []
    monopoly_inns: list[str] = []
    manufacturer_counts: dict[str, int] = {}

    for inn, items in licemed_data.items():
        manufacturers = set()
        for item in items:
            mfr = item.get("manufacturer", "").strip()
            if mfr and mfr != "-":
                manufacturers.add(mfr)

            expiry_str = item.get("expiry_date", "")
            if expiry_str:
                try:
                    expiry = datetime.date.fromisoformat(expiry_str)
                    if today <= expiry <= two_months_later:
                        expiring_soon.append({
                            "inn": inn,
                            "brand": item.get("brand_name", ""),
                            "expiry": expiry_str,
                            "importer": item.get("importer", ""),
                        })
                except ValueError:
                    pass

        count = len(manufacturers)
        manufacturer_counts[inn] = count
        if 0 < count < 3:
            monopoly_inns.append(inn)

    return {
        "expiring_soon": expiring_soon,
        "monopoly_inns": monopoly_inns,
        "manufacturer_counts": manufacturer_counts,
        "total_registrations": sum(len(v) for v in licemed_data.values()),
    }
