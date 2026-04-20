"""몽골 보건의료보험청 (EMD) 약가 고시 크롤러.

대상:
  - https://emd.gov.mn/pages/13  — 필수의약품 가격 상한 고시 (PDF/Excel)
  - https://emd.gov.mn           — 계약 약국(Contracted Pharmacies) 목록

수집 데이터:
  - 약품명 (Drug Name)
  - INN 성분명
  - 최대 소매 가격 (Maximum Retail Price, MNT)
  - HIF 상환액 (Health Insurance Fund Reimbursement, MNT)
  - 본인부담금 상한 (Copayment Ceiling, MNT)
  - 계약 약국 명칭·지역(아이막)·연락처

전략적 가치:
  - 수출 단가가 MRP 상한 초과 시 현지 파트너 경쟁력 급락 → FOB 설계 제약 조건
  - 아이막별 계약 약국 밀도 → 최적 도매 파트너 선정
"""

from __future__ import annotations

import io
import re
from typing import Any

EMD_BASE = "https://emd.gov.mn"
PRICING_PAGE = f"{EMD_BASE}/pages/13"
PHARMACY_PAGE = f"{EMD_BASE}/pages/contracted-pharmacies"


def _extract_pdf_links(html: str, base_url: str) -> list[str]:
    """HTML에서 PDF/Excel 파일 링크 추출."""
    links: list[str] = []
    patterns = [
        r'href=["\']([^"\']+\.(?:pdf|xlsx|xls))["\']',
        r'href=["\']([^"\']+/download/[^"\']+)["\']',
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, html, re.I):
            href = m.group(1)
            if href.startswith("http"):
                links.append(href)
            else:
                links.append(base_url.rstrip("/") + "/" + href.lstrip("/"))
    return list(dict.fromkeys(links))  # 중복 제거


def _parse_excel_pricing(content: bytes) -> list[dict[str, Any]]:
    """Excel 바이트에서 약가 테이블 파싱."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
    except Exception:
        try:
            import xlrd
            wb = xlrd.open_workbook(file_contents=content)
            ws = wb.sheet_by_index(0)
            rows = [ws.row_values(i) for i in range(ws.nrows)]
        except Exception:
            return []

    results: list[dict[str, Any]] = []
    header_row: list[str] = []

    col_map: dict[str, int] = {}
    HEADER_ALIASES: dict[str, list[str]] = {
        "drug_name":       ["нэр", "name", "drug", "препарат", "эмийн нэр"],
        "inn_name":        ["inn", "олон улсын", "international"],
        "price_mnt":       ["үнэ", "price", "дээд үнэ", "mrp", "maximum"],
        "hif_reimburse":   ["даатгал", "insurance", "hif", "нөхөн"],
        "copayment":       ["иргэн", "copay", "өөрийн"],
    }

    for i, row in enumerate(rows):
        str_row = [str(c or "").strip().lower() for c in row]
        if not header_row:
            matched = 0
            for aliases in HEADER_ALIASES.values():
                if any(any(a in cell for a in aliases) for cell in str_row):
                    matched += 1
            if matched >= 2:
                header_row = str_row
                for col_key, aliases in HEADER_ALIASES.items():
                    for j, cell in enumerate(str_row):
                        if any(a in cell for a in aliases):
                            col_map[col_key] = j
                            break
            continue

        if not any(row):
            continue

        def _get(key: str) -> str:
            idx = col_map.get(key)
            if idx is None or idx >= len(row):
                return ""
            return str(row[idx] or "").strip()

        def _get_num(key: str) -> float | None:
            val = _get(key)
            val = re.sub(r"[^\d.]", "", val)
            try:
                return float(val)
            except ValueError:
                return None

        drug_name = _get("drug_name")
        if not drug_name:
            continue

        results.append({
            "drug_name": drug_name,
            "inn_name": _get("inn_name"),
            "price_mnt": _get_num("price_mnt"),
            "hif_reimbursement_mnt": _get_num("hif_reimburse"),
            "copayment_mnt": _get_num("copayment"),
            "source_site": "emd_pricing",
            "source_url": PRICING_PAGE,
        })

    return results


def _parse_pdf_pricing(content: bytes) -> list[dict[str, Any]]:
    """PDF 바이트에서 약가 테이블 파싱 (pdfplumber 사용)."""
    try:
        import pdfplumber
    except ImportError:
        return []

    results: list[dict[str, Any]] = []
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row or all(c is None for c in row):
                            continue
                        str_row = [str(c or "").strip() for c in row]
                        if len(str_row) < 3:
                            continue

                        drug_name = str_row[0]
                        if not drug_name or drug_name.lower() in ("нэр", "name", ""):
                            continue

                        price_mnt: float | None = None
                        for cell in str_row[1:]:
                            clean = re.sub(r"[^\d.]", "", cell)
                            try:
                                v = float(clean)
                                if v > 0:
                                    price_mnt = v
                                    break
                            except ValueError:
                                continue

                        results.append({
                            "drug_name": drug_name,
                            "inn_name": str_row[1] if len(str_row) > 1 else "",
                            "price_mnt": price_mnt,
                            "hif_reimbursement_mnt": None,
                            "copayment_mnt": None,
                            "source_site": "emd_pricing",
                            "source_url": PRICING_PAGE,
                        })
    except Exception:
        pass

    return results


async def crawl_emd_pricing() -> list[dict[str, Any]]:
    """EMD 약가 고시 페이지에서 파일 다운로드 후 파싱."""
    try:
        import httpx
    except ImportError:
        return []

    all_results: list[dict[str, Any]] = []

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)",
        "Accept-Language": "mn,en;q=0.9",
    }

    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(PRICING_PAGE)
            resp.raise_for_status()
            html = resp.text

            file_links = _extract_pdf_links(html, EMD_BASE)

            for link in file_links[:10]:  # 최대 10개 파일
                try:
                    file_resp = await client.get(link, timeout=30.0)
                    file_resp.raise_for_status()
                    content = file_resp.content

                    if link.lower().endswith((".xlsx", ".xls")):
                        parsed = _parse_excel_pricing(content)
                    elif link.lower().endswith(".pdf"):
                        parsed = _parse_pdf_pricing(content)
                    else:
                        continue

                    for item in parsed:
                        item["file_url"] = link
                    all_results.extend(parsed)

                except Exception:
                    continue

    except Exception:
        pass

    return all_results


async def crawl_contracted_pharmacies() -> list[dict[str, Any]]:
    """EMD 계약 약국 목록 수집 (아이막별 지리 분포 분석용)."""
    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    results: list[dict[str, Any]] = []
    headers = {"User-Agent": "Mozilla/5.0 (compatible; PharmaResearch/1.0)"}

    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=20.0) as client:
            resp = await client.get(PHARMACY_PAGE)
            if resp.status_code != 200:
                resp = await client.get(f"{EMD_BASE}/contracted-organizations")
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            rows = soup.select("table tbody tr, .pharmacy-item")

            for row in rows:
                cells = row.find_all(["td", "li", "div"])
                if not cells:
                    continue
                text_cells = [c.get_text(strip=True) for c in cells]
                if not text_cells[0]:
                    continue

                aimag = ""
                for cell in text_cells:
                    aimag_patterns = [
                        "аймаг", "Aimag", "дүүрэг", "хот",
                        "Улаанбаатар", "Ulaanbaatar",
                    ]
                    if any(p in cell for p in aimag_patterns):
                        aimag = cell
                        break

                results.append({
                    "pharmacy_name": text_cells[0],
                    "aimag": aimag,
                    "address": text_cells[1] if len(text_cells) > 1 else "",
                    "contact": text_cells[2] if len(text_cells) > 2 else "",
                    "source_site": "emd_pharmacy",
                    "source_url": PHARMACY_PAGE,
                })

    except Exception:
        pass

    return results


def match_to_products(
    pricing_rows: list[dict[str, Any]],
    target_inns: list[str],
) -> dict[str, list[dict[str, Any]]]:
    """수집된 약가 데이터를 자사 8품목 INN과 매칭."""
    matched: dict[str, list[dict[str, Any]]] = {inn: [] for inn in target_inns}

    for row in pricing_rows:
        drug_text = (
            row.get("drug_name", "") + " " +
            row.get("inn_name", "")
        ).lower()

        for inn in target_inns:
            if inn.lower() in drug_text:
                matched[inn].append(row)

    return matched
