"""Verified Mongolia buyer candidates for the P3 buyer pipeline.

The CPHI crawler is useful for finding global manufacturers and partners, but
Mongolia sales work needs local importers, wholesalers, and pharmacy chains.
This module keeps a small vetted seed list from public company pages so the
buyer report still contains contactable Mongolia-side candidates when CPHI is
slow, blocked, or skewed toward API manufacturers.
"""

from __future__ import annotations

from typing import Any


_PRODUCT_FIT: dict[str, dict[str, list[str]]] = {
    "MN_sereterol_activair": {
        "ingredients": ["Fluticasone", "Salmeterol"],
        "areas": ["respiratory", "hospital", "pharmacy"],
    },
    "MN_omethyl_omega3_2g": {
        "ingredients": ["Omega-3"],
        "areas": ["cardiovascular", "pharmacy", "otc"],
    },
    "MN_hydrine_hydroxyurea_500": {
        "ingredients": ["Hydroxyurea"],
        "areas": ["oncology", "hospital", "tender"],
    },
    "MN_gadvoa_gadobutrol_604": {
        "ingredients": ["Gadobutrol"],
        "areas": ["diagnostic", "hospital", "medical devices"],
    },
    "MN_rosumeg_combigel": {
        "ingredients": ["Rosuvastatin", "Omega-3"],
        "areas": ["cardiovascular", "pharmacy"],
    },
    "MN_atmeg_combigel": {
        "ingredients": ["Atorvastatin", "Omega-3"],
        "areas": ["cardiovascular", "pharmacy"],
    },
    "MN_ciloduo_cilosta_rosuva": {
        "ingredients": ["Cilostazol", "Rosuvastatin"],
        "areas": ["cardiovascular", "hospital", "pharmacy"],
    },
    "MN_gastiin_cr_mosapride": {
        "ingredients": ["Mosapride"],
        "areas": ["gastroenterology", "hospital", "pharmacy"],
    },
}


_BUYERS: list[dict[str, Any]] = [
    {
        "id": "mn_monos_trade",
        "company_name": "Monos Trade LLC",
        "website": "https://monostrade.mn/eng",
        "email": "",
        "phone": "+976 7766 6688",
        "address": "Mongol 99 Building, Dund Gol Street, Bayangol District, Ulaanbaatar",
        "focus_tags": ["import", "distribution", "hospital", "public", "private", "vaccine", "biological"],
        "employees": "450+ group-level employees",
        "territories": ["Mongolia"],
        "certifications": ["ISO 9001:2015 quality management"],
        "overview": (
            "Monos Trade is a Monos group distributor importing and distributing drugs, "
            "medical products, laboratory equipment, diagnostics, vaccines, and biological "
            "preparations to public and private health institutions in Mongolia."
        ),
        "source_urls": ["https://monostrade.mn/eng", "https://monospharmatrade.mn/"],
    },
    {
        "id": "mn_tsombo",
        "company_name": "Tsombo LLC",
        "website": "https://www.tsombo.mn/p/6",
        "email": "info@tsombo.mn",
        "phone": "11-318312 / +976 85114445 / +976 85113338",
        "address": "Building 51, Juulchin Street, Chingeltei District, Ulaanbaatar",
        "focus_tags": ["import", "distribution", "hospital", "pharmacy", "tender", "oncology", "injection"],
        "employees": "",
        "territories": ["Mongolia"],
        "certifications": ["GMP approved injectable factory investment"],
        "overview": (
            "Tsombo imports medicines and medical equipment from more than 20 countries "
            "and supplies hospitals and pharmacies across Mongolia through tender and "
            "non-tender channels. It has supplied chemotherapy drugs and injections "
            "nationwide since 2013."
        ),
        "source_urls": ["https://www.tsombo.mn/p/6", "https://www.tsombo.mn/?locale=en"],
    },
    {
        "id": "mn_ento",
        "company_name": "ENTO LLC",
        "website": "https://ento.mn/en/business-area/ento",
        "email": "support@ento.mn",
        "phone": "+976 7012 1211",
        "address": "Narny Zam-89, Sukhbaatar District, Ulaanbaatar",
        "focus_tags": ["import", "wholesale", "pharmacy", "hospital", "medical devices", "private"],
        "employees": "250+",
        "territories": ["Ulaanbaatar", "21 provinces of Mongolia"],
        "certifications": [],
        "overview": (
            "ENTO operates a pharmaceutical wholesale center, imports medicines and "
            "medical devices, and supplies healthcare institutions, pharmacies, and "
            "hospitals across Ulaanbaatar and all 21 Mongolian provinces."
        ),
        "source_urls": ["https://ento.mn/en", "https://ento.mn/en/business-area/ento"],
    },
    {
        "id": "mn_gamba",
        "company_name": "Gamba Trade LLC",
        "website": "https://gamba.mn/",
        "email": "ganbayar@gamba.mn",
        "phone": "+976 99196242 / +976 95708695",
        "address": "Ulaanbaatar, Mongolia",
        "focus_tags": ["wholesale", "manufacturing", "pharmacy", "otc", "prescription"],
        "employees": "",
        "territories": ["Mongolia"],
        "certifications": [],
        "overview": (
            "Gamba Trade is a pharmaceutical wholesaler, manufacturer, and pharmacy "
            "chain. It works with more than 35 wholesalers and reaches about 3000 "
            "pharmacies through its network."
        ),
        "source_urls": ["https://gamba.mn/"],
    },
    {
        "id": "mn_tukhum",
        "company_name": "Tukhum Global Pharma",
        "website": "https://www.tukhumglobal.com/",
        "email": "info@tukhumglobal.com",
        "phone": "",
        "address": "Sky Plaza Business Center, Embassy Road, Ulaanbaatar",
        "focus_tags": ["wholesale", "distribution", "hospital", "pharmacy", "registration"],
        "employees": "",
        "territories": ["Mongolia"],
        "certifications": [],
        "overview": (
            "Tukhum Global Pharma is a pharmaceutical wholesaler distributing medicines "
            "and medical devices to wholesalers, hospitals, and pharmacies in Mongolia. "
            "Its public page states that it looks for worldwide partners and handles "
            "registration and distribution."
        ),
        "source_urls": ["https://www.tukhumglobal.com/"],
    },
    {
        "id": "mn_grandmed_pharm",
        "company_name": "GrandMed Pharm LLC",
        "website": "https://en.jiguurgrand.mn/grandpharm",
        "email": "",
        "phone": "7706-6644 / +976 7555-4455",
        "address": "Mahatma Gandhi Street, Khan-Uul District, Ulaanbaatar",
        "focus_tags": ["import", "wholesale", "hospital", "pharmacy", "korea", "china", "diagnostic"],
        "employees": "",
        "territories": ["Mongolia"],
        "certifications": ["licensed importer of medicines and medical products"],
        "overview": (
            "GrandMed Pharm imports and wholesales medicines, medical supplies, "
            "diagnostic tools, and medical equipment. It supplies GrandMed Hospital "
            "and major public and private hospitals in Mongolia, with distributor "
            "relationships involving South Korean and Chinese manufacturers."
        ),
        "source_urls": ["https://en.jiguurgrand.mn/grandpharm"],
    },
    {
        "id": "mn_ariunmongol",
        "company_name": "Ariunmongol Co., Ltd",
        "website": "https://www.ariunmongol.com/english/about-us",
        "email": "foreignrelations@ariunmongol.com",
        "phone": "",
        "address": "Ulaanbaatar, Mongolia",
        "focus_tags": ["manufacturing", "trade", "import", "pharmacy", "gmp", "traditional", "antibiotic"],
        "employees": "",
        "territories": ["Mongolia"],
        "certifications": ["ISO 9001:2015", "Mongolian GMP-standard facilities"],
        "overview": (
            "Ariunmongol is one of Mongolia's founding pharmaceutical manufacturers "
            "and also operates trade, service, export, import, supply distribution, "
            "and retail pharmacy functions."
        ),
        "source_urls": ["https://www.ariunmongol.com/english/about-us"],
    },
    {
        "id": "mn_meic",
        "company_name": "Mongol Em Impex Concern LLC (MEIC)",
        "website": "http://www.meic.mn",
        "email": "",
        "phone": "",
        "address": "MEIC Building, Teerverchid Street No. 39, Sukhbaatar District, Ulaanbaatar",
        "focus_tags": ["import", "wholesale", "retail", "national distribution", "pharmacy"],
        "employees": "",
        "territories": ["Mongolia"],
        "certifications": [],
        "overview": (
            "MEIC traces its history to Mongolia's first pharmacy company and is a "
            "recognized local pharmaceutical distribution candidate with Ulaanbaatar "
            "address and public company profiles."
        ),
        "source_urls": [
            "https://www.odoo.com/ru_RU/customers/mongol-em-impex-concern-llc-meic-11655440",
            "https://chemdmart.com/company-profile/mongol-em-impex-concern-llc",
        ],
    },
]


def _fit_score(buyer: dict[str, Any], product_key: str) -> tuple[bool, list[str], list[str]]:
    fit = _PRODUCT_FIT.get(product_key, {"ingredients": [], "areas": []})
    areas = [a.lower() for a in fit.get("areas", [])]
    tags = [t.lower() for t in buyer.get("focus_tags", [])]
    matched_areas = [a for a in areas if any(a in t or t in a for t in tags)]
    broad_channel = any(t in tags for t in ("import", "distribution", "wholesale", "hospital", "pharmacy"))
    return bool(matched_areas or broad_channel), fit.get("ingredients", []), matched_areas


def _as_pipeline_candidate(buyer: dict[str, Any], product_key: str, product_label: str) -> dict[str, Any]:
    ingredient_match, ingredients, matched_areas = _fit_score(buyer, product_key)
    contact_bits = [
        buyer.get("email") or "",
        buyer.get("phone") or "",
        buyer.get("website") or "",
    ]
    contact_quality = sum(1 for bit in contact_bits if str(bit).strip())
    reason = (
        f"{buyer['company_name']} is a Mongolia-side buyer candidate for {product_label or product_key}. "
        f"Public sources describe it as active in {', '.join(buyer.get('focus_tags', [])[:5])}. "
        "Because it has local import, wholesale, hospital, or pharmacy channels, it is suitable for first outreach "
        "before broader CPHI manufacturer leads."
    )
    if matched_areas:
        reason += f" Product fit is especially relevant to {', '.join(matched_areas)}."

    enriched = {
        "revenue": "-",
        "employees": buyer.get("employees") or "-",
        "founded": "-",
        "territories": buyer.get("territories", ["Mongolia"]),
        "has_target_country_presence": True,
        "has_gmp": bool([c for c in buyer.get("certifications", []) if "GMP" in c.upper()]),
        "import_history": "import" in [t.lower() for t in buyer.get("focus_tags", [])],
        "procurement_history": any(t in [x.lower() for x in buyer.get("focus_tags", [])] for t in ("tender", "public")),
        "has_pharmacy_chain": "pharmacy" in [t.lower() for t in buyer.get("focus_tags", [])],
        "public_channel": any(t in [x.lower() for x in buyer.get("focus_tags", [])] for t in ("public", "hospital", "tender")),
        "private_channel": any(t in [x.lower() for x in buyer.get("focus_tags", [])] for t in ("private", "pharmacy", "wholesale")),
        "mah_capable": any(t in [x.lower() for x in buyer.get("focus_tags", [])] for t in ("registration", "import")),
        "korea_experience": "Yes" if "korea" in [t.lower() for t in buyer.get("focus_tags", [])] else "-",
        "certifications": buyer.get("certifications", []),
        "source_urls": buyer.get("source_urls", []),
        "company_overview_kr": buyer.get("overview", ""),
        "recommendation_reason": reason,
        "contact_quality": contact_quality,
    }

    full_text = " ".join(
        str(x)
        for x in [
            buyer["company_name"],
            buyer.get("overview", ""),
            buyer.get("address", ""),
            buyer.get("phone", ""),
            buyer.get("email", ""),
            " ".join(buyer.get("focus_tags", [])),
        ]
        if x
    )
    return {
        "exid": buyer["id"],
        "company_name": buyer["company_name"],
        "country": "Mongolia",
        "address": buyer.get("address") or "-",
        "phone": buyer.get("phone") or "-",
        "fax": "-",
        "email": buyer.get("email") or "-",
        "website": buyer.get("website") or "-",
        "booth": "-",
        "category": "Verified Mongolia importer/distributor",
        "products_cphi": ingredients,
        "overview_text": buyer.get("overview", ""),
        "full_page_text": full_text[:6000],
        "ingredient_match": ingredient_match,
        "matched_ingredients": ingredients,
        "matched_therapeutic_areas": matched_areas,
        "source_region": "verified_mn_buyer",
        "skip_ai_enrich": True,
        "enriched": enriched,
    }


def get_verified_mn_buyers(product_key: str, product_label: str = "") -> list[dict[str, Any]]:
    return [_as_pipeline_candidate(b, product_key, product_label) for b in _BUYERS]


def merge_buyer_candidates(
    primary: list[dict[str, Any]],
    secondary: list[dict[str, Any]],
    limit: int = 20,
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in [*primary, *secondary]:
        key = (
            str(item.get("company_name") or item.get("exid") or "").strip().lower(),
            str(item.get("website") or "").strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
        if len(merged) >= limit:
            break
    return merged
