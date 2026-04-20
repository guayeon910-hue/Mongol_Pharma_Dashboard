"""몽골 주요 제약 유통사 포트폴리오 크롤러.

대상 유통사:
  - Monos Group     https://monos.mn         (시장 점유율 1위)
  - MEIC Pharmmarket https://pharmmarket.mn  (역사적 유통사, 전국 약국망)
  - Gobi Gate Pharma https://gobigate.com    (GMP 전문의약품 특화)
  - Lenus Med LLC   https://lenusmed.mn      (신흥 유통사, 파트너십 적극)
  - Asia Pharma LLC  (호흡기·알레르기 라인업)

수집 데이터:
  - 취급 품목 카탈로그 (INN, 브랜드명, 제조사, 치료 영역)
  - 포장 단위 및 규격
  - 공급 제조사 명단
  - 파트너십 문의 페이지 콘텐츠

전략적 가치:
  - 유통사별 포트폴리오 공백(White Space) 식별
  - 자사 8품목과 중복되는 파이프라인 경쟁 분석
  - 파트너 제안서(Pitching Strategy) 근거 데이터
"""

from __future__ import annotations

import asyncio
from typing import Any

DISTRIBUTORS: list[dict[str, str]] = [
    {
        "id": "monos",
        "name": "Monos Group",
        "url": "https://monos.mn",
        "catalog_url": "https://monos.mn/products",
        "focus": "심혈관·소화기 포함 전 품목 (8,000+)",
    },
    {
        "id": "meic",
        "name": "Mongol Em Impex Concern (MEIC)",
        "url": "https://pharmmarket.mn",
        "catalog_url": "https://pharmmarket.mn/catalog",
        "focus": "80개국 파트너, 전국 Pharmmarket 약국 체인",
    },
    {
        "id": "gobigate",
        "name": "Gobi Gate Pharmaceuticals",
        "url": "https://gobigate.com",
        "catalog_url": "https://gobigate.com/products",
        "focus": "GMP 인증 전문의약품 (항암·심혈관·당뇨)",
    },
    {
        "id": "lenusmed",
        "name": "Lenus Med LLC",
        "url": "https://lenusmed.mn",
        "catalog_url": "https://lenusmed.mn/services",
        "focus": "신흥 유통사, 해외 제조사 발굴 적극",
    },
]

TARGET_INNS: list[str] = [
    "Rosuvastatin", "Atorvastatin", "Cilostazol", "Omega-3",
    "Gadobutrol", "Hydroxyurea", "Fluticasone", "Salmeterol", "Mosapride",
]

THERAPEUTIC_AREAS: dict[str, str] = {
    "Rosuvastatin":  "cardiovascular",
    "Atorvastatin":  "cardiovascular",
    "Cilostazol":    "cardiovascular",
    "Omega-3":       "cardiovascular",
    "Gadobutrol":    "diagnostic",
    "Hydroxyurea":   "oncology",
    "Fluticasone":   "respiratory",
    "Salmeterol":    "respiratory",
    "Mosapride":     "gastroenterology",
}


def _extract_product_catalog(html: str, distributor_id: str) -> list[dict[str, Any]]:
    """유통사 카탈로그 HTML에서 품목 정보 추출 (NLP 기반)."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    import re

    soup = BeautifulSoup(html, "html.parser")
    products: list[dict[str, Any]] = []

    product_els = soup.select(
        ".product-item, .drug-item, .medicine-item, "
        "table tbody tr, .catalog-item, article"
    )

    for el in product_els:
        text = el.get_text(separator=" ", strip=True)
        if len(text) < 5:
            continue

        # INN 매칭
        matched_inns: list[str] = []
        for inn in TARGET_INNS:
            if inn.lower() in text.lower():
                matched_inns.append(inn)

        # 함량 추출
        mg_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:mg|мг)", text, re.I)
        strength = mg_m.group(0) if mg_m else ""

        # 포장 단위
        pack_m = re.search(r"(\d+)\s*(?:ширхэг|шир|tab|cap|amp|pcs|ml)", text, re.I)
        pack_size = pack_m.group(0) if pack_m else ""

        products.append({
            "raw_text": text[:400],
            "matched_inns": matched_inns,
            "strength": strength,
            "pack_size": pack_size,
            "distributor_id": distributor_id,
            "therapeutic_areas": list({
                THERAPEUTIC_AREAS.get(inn, "other") for inn in matched_inns
            }),
        })

    return [p for p in products if p["matched_inns"] or len(p["raw_text"]) > 20]


async def crawl_distributor(
    distributor: dict[str, str],
    emit: Any = None,
) -> list[dict[str, Any]]:
    """단일 유통사 카탈로그 크롤링."""
    try:
        import httpx
    except ImportError:
        return []

    results: list[dict[str, Any]] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
        "Accept-Language": "mn,en;q=0.9",
    }
    d_id = distributor["id"]
    url = distributor.get("catalog_url", distributor["url"])

    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=20.0) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                resp = await client.get(distributor["url"])
            resp.raise_for_status()

            products = _extract_product_catalog(resp.text, d_id)
            results.extend(products)

            if emit:
                await emit({
                    "phase": "distributor",
                    "message": f"{distributor['name']} — {len(products)}개 품목 수집",
                    "level": "success" if products else "warn",
                })

    except Exception as e:
        if emit:
            await emit({
                "phase": "distributor",
                "message": f"{distributor['name']} 오류: {str(e)[:80]}",
                "level": "warn",
            })

    return results


async def crawl_all_distributors(
    emit: Any = None,
) -> dict[str, list[dict[str, Any]]]:
    """전체 유통사 병렬 크롤링."""
    tasks = [crawl_distributor(d, emit=emit) for d in DISTRIBUTORS]
    results_list = await asyncio.gather(*tasks, return_exceptions=True)

    all_results: dict[str, list[dict[str, Any]]] = {}
    for distributor, result in zip(DISTRIBUTORS, results_list):
        if isinstance(result, Exception):
            all_results[distributor["id"]] = []
        else:
            all_results[distributor["id"]] = result  # type: ignore[assignment]

    return all_results


def find_whitespace(
    distributor_data: dict[str, list[dict[str, Any]]],
) -> dict[str, list[str]]:
    """각 유통사 포트폴리오의 공백(White Space) 식별.

    Returns:
        dict: {distributor_id: [missing_inn_list]}
    """
    whitespace: dict[str, list[str]] = {}

    for d_id, products in distributor_data.items():
        covered_inns: set[str] = set()
        for product in products:
            covered_inns.update(product.get("matched_inns", []))

        missing = [inn for inn in TARGET_INNS if inn not in covered_inns]
        whitespace[d_id] = missing

    return whitespace


def score_partners(
    distributor_data: dict[str, list[dict[str, Any]]],
    tender_ranking: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """유통사별 파트너 적합성 점수 산출.

    기준:
      - 포트폴리오 공백 수 (자사 품목 취급 공간 많을수록 유리)
      - 공공 입찰 낙찰 이력 (tender_ranking 연동)
      - 항암/조영제 전문성 (하이드린·가드보아 주 우선)
    """
    vendor_awards: dict[str, int] = {}
    if tender_ranking:
        for rank_item in tender_ranking:
            vendor_awards[rank_item["vendor_name"]] = rank_item.get("win_count", 0)

    scored: list[dict[str, Any]] = []
    for dist in DISTRIBUTORS:
        d_id = dist["id"]
        products = distributor_data.get(d_id, [])

        covered: set[str] = set()
        for p in products:
            covered.update(p.get("matched_inns", []))

        oncology_score = 1 if "Hydroxyurea" not in covered else 0
        contrast_score = 1 if "Gadobutrol" not in covered else 0
        whitespace_score = len(TARGET_INNS) - len(covered)
        tender_score = vendor_awards.get(dist["name"], 0)

        total_score = whitespace_score * 2 + oncology_score * 5 + contrast_score * 3 + tender_score

        scored.append({
            "distributor_id": d_id,
            "distributor_name": dist["name"],
            "url": dist["url"],
            "focus": dist["focus"],
            "covered_inns": list(covered),
            "missing_inns": [i for i in TARGET_INNS if i not in covered],
            "whitespace_count": whitespace_score,
            "tender_wins": tender_score,
            "partner_score": total_score,
        })

    scored.sort(key=lambda x: x["partner_score"], reverse=True)
    return scored
