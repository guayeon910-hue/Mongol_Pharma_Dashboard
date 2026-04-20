"""몽골 의약품·의료기기 규제청 (MMRA) 규제 공시 크롤러.

대상:
  - https://mmra.gov.mn  — MMRA 공식 포털
  - https://moh.gov.mn/home — 보건부 포털 (상위 정책 공시)

수집 데이터:
  - 법령 개정안 (Legislation) 첨부파일 (PDF/Word)
  - 약물 감시 안전성 서한 (Pharmacovigilance Safety Letters)
  - 의약품 광고 허가 내역
  - 인허가 심의 결과 공지
  - 이상반응(ADR) 보고서

전략적 가치:
  - 광고 허가 심의 기준 분석 → 임상 소구점 선제 대응
  - 경쟁 성분 ADR 보고 감시 → 안전성 우위 논리 구축
  - 법령 개정 실시간 감지 → 인허가 절차 변화 대응
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

MMRA_BASE = "https://mmra.gov.mn"
MOH_BASE = "https://moh.gov.mn"

SECTION_PATTERNS: dict[str, list[str]] = {
    "legislation": ["legislation", "law", "хууль", "дүрэм", "журнал"],
    "safety":      ["pharmacovigilance", "safety", "аюулгүй", "гаж нөлөө", "adr"],
    "advertising": ["advertising", "зар", "сурталчилгаа"],
    "approval":    ["approval", "registration", "бүртгэл", "зөвшөөрөл"],
}


def _classify_notice(title: str, content: str) -> str:
    text = (title + " " + content).lower()
    for category, patterns in SECTION_PATTERNS.items():
        if any(p in text for p in patterns):
            return category
    return "general"


async def _fetch_html(session: Any, url: str) -> str:
    try:
        resp = await session.get(url, timeout=15.0)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return ""


def _extract_attachments(html: str, base_url: str) -> list[dict[str, str]]:
    """HTML에서 PDF/Word 첨부파일 링크 추출."""
    attachments: list[dict[str, str]] = []
    pattern = r'href=["\']([^"\']+\.(?:pdf|docx?|xlsx?))["\'][^>]*>([^<]*)<'
    for m in re.finditer(pattern, html, re.I):
        href = m.group(1)
        label = m.group(2).strip()
        url = href if href.startswith("http") else base_url.rstrip("/") + "/" + href.lstrip("/")
        attachments.append({"url": url, "label": label})
    return attachments


def _parse_notice_list(html: str, base_url: str) -> list[dict[str, Any]]:
    """공지사항 목록 HTML 파싱."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    soup = BeautifulSoup(html, "html.parser")
    notices: list[dict[str, Any]] = []

    items = soup.select(".news-item, .notice-item, .post-item, article, .list-item")
    if not items:
        items = soup.select("li, tr")

    for item in items:
        title_el = item.select_one("h2, h3, h4, .title, td:first-child, a")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title or len(title) < 5:
            continue

        link_el = item.select_one("a[href]")
        link = ""
        if link_el:
            href = link_el.get("href", "")
            link = href if href.startswith("http") else base_url.rstrip("/") + "/" + href.lstrip("/")

        date_el = item.select_one(".date, time, .post-date, td:last-child")
        date = date_el.get_text(strip=True) if date_el else ""

        content_text = item.get_text(strip=True)
        attachments = _extract_attachments(str(item), base_url)

        notices.append({
            "title": title,
            "link": link,
            "date": date,
            "category": _classify_notice(title, content_text),
            "attachments": attachments,
            "raw_text": content_text[:500],
            "source_site": "mmra",
            "source_url": base_url,
        })

    return notices


async def crawl_mmra_notices(
    max_pages: int = 5,
    emit: Any = None,
) -> list[dict[str, Any]]:
    """MMRA 공지사항 전체 수집."""
    try:
        import httpx
    except ImportError:
        return []

    all_notices: list[dict[str, Any]] = []
    sections = [
        f"{MMRA_BASE}/news",
        f"{MMRA_BASE}/legislation",
        f"{MMRA_BASE}/pharmacovigilance",
        f"{MOH_BASE}/news",
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
        "Accept-Language": "mn,en;q=0.9",
    }

    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=20.0) as session:
            for section_url in sections:
                for page in range(1, max_pages + 1):
                    page_url = f"{section_url}?page={page}" if page > 1 else section_url
                    html = await _fetch_html(session, page_url)
                    if not html:
                        break

                    notices = _parse_notice_list(html, MMRA_BASE)
                    if not notices:
                        break

                    all_notices.extend(notices)

                    if emit:
                        await emit({
                            "phase": "mmra",
                            "message": f"MMRA {section_url} p{page} — {len(notices)}건",
                            "level": "info",
                        })

                    await asyncio.sleep(1.5)

    except Exception:
        pass

    return all_notices


def filter_by_target_inns(
    notices: list[dict[str, Any]],
    target_inns: list[str],
) -> list[dict[str, Any]]:
    """자사 8품목 관련 공지사항만 필터링."""
    filtered: list[dict[str, Any]] = []
    for notice in notices:
        text = (notice.get("title", "") + " " + notice.get("raw_text", "")).lower()
        for inn in target_inns:
            if inn.lower() in text:
                notice_copy = dict(notice)
                notice_copy["matched_inn"] = inn
                filtered.append(notice_copy)
                break
    return filtered


async def extract_adr_reports(
    notices: list[dict[str, Any]],
    target_inns: list[str],
) -> list[dict[str, Any]]:
    """ADR(이상반응) 보고서 전용 추출."""
    adr_notices = [
        n for n in notices
        if n.get("category") == "safety"
    ]
    return filter_by_target_inns(adr_notices, target_inns)
