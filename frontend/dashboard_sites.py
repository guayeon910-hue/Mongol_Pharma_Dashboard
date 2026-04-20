"""대시보드에 표시할 몽골(MN) 소스 라벨 (한국어)."""

from __future__ import annotations

from typing import Any, TypedDict


class SiteDef(TypedDict):
    id: str
    name: str
    hint: str
    domain: str
    tier: int


DASHBOARD_SITES: tuple[SiteDef, ...] = (
    # ── Tier 1: 규제·인허가 ──────────────────────────────────────────────────
    {
        "id": "mmra",
        "name": "MMRA · 의약품·의료기기 규제청",
        "hint": "법령 개정안·약물 감시 안전성 서한·광고 허가 내역 (PDF/Word 첨부파일 파싱)",
        "domain": "mmra.gov.mn",
        "tier": 1,
    },
    {
        "id": "licemed",
        "name": "Licemed · 국가의약품 통합 등록 DB",
        "hint": "4,500+ 품목 SPC·인허가 만료일·제조사·수입유통사 매핑 (E-Mongolia)",
        "domain": "licemed.mohs.mn",
        "tier": 1,
    },
    # ── Tier 2: 약가·공공조달 ────────────────────────────────────────────────
    {
        "id": "emd_pricing",
        "name": "EMD · 보건의료보험청 약가 고시",
        "hint": "590종 필수의약품 최대소매가(MNT) + HIF 상환액 PDF/Excel 파싱",
        "domain": "emd.gov.mn",
        "tier": 2,
    },
    {
        "id": "tender",
        "name": "tender.gov.mn · 국가 전자조달",
        "hint": "의약품 카테고리 입찰공고·낙찰자·계약금액 OCDS 파싱 (17,000+ 건/반기)",
        "domain": "tender.gov.mn",
        "tier": 2,
    },
    {
        "id": "ecepp",
        "name": "ECEPP · EBRD 국제조달 포털",
        "hint": "ADB/EBRD 몽골 보건 프로젝트 달러 기반 국제 경쟁 입찰 모니터링",
        "domain": "ecepp.ebrd.com",
        "tier": 2,
    },
    # ── Tier 3: 거시통계·유통사 ─────────────────────────────────────────────
    {
        "id": "monos",
        "name": "Monos Group · 시장 점유율 1위",
        "hint": "8,000+ 품목 카탈로그 — 심혈관·소화기 경쟁 파이프라인 교차 분석 (Playwright)",
        "domain": "monos.mn",
        "tier": 3,
    },
    {
        "id": "meic",
        "name": "MEIC Pharmmarket · 전국 약국 체인",
        "hint": "1923년 설립 역사적 유통사 — 80개국 파트너, 수입 마진 구조 리버스 엔지니어링",
        "domain": "pharmmarket.mn",
        "tier": 3,
    },
    {
        "id": "gobigate",
        "name": "Gobi Gate Pharma · GMP 전문의약품",
        "hint": "항암·심혈관·당뇨 특화 — 하이드린·가드보아 주 파트너 적합성 평가",
        "domain": "gobigate.com",
        "tier": 3,
    },
    {
        "id": "lenusmed",
        "name": "Lenus Med · 신흥 유통사",
        "hint": "2020년 설립 — 신규 해외 제조사 발굴 적극, 제휴 문의 모니터링",
        "domain": "lenusmed.mn",
        "tier": 3,
    },
)


def initial_site_states() -> dict[str, dict[str, Any]]:
    return {
        s["id"]: {
            "status": "pending",
            "message": "아직 시작 전이에요",
            "ts": 0.0,
            "tier": s["tier"],
        }
        for s in DASHBOARD_SITES
    }
