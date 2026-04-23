"""Shared Supabase helpers for SG, MN, and UY dashboards."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

_DEFAULT_URL = "https://oynefikqoibwtfpjlizv.supabase.co"
_DEFAULT_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im95bmVmaWtxb2lid3RmcGpsaXp2Iiwicm9sZSI6"
    "InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjA1NzgwMywiZXhwIjoyMDkxNjMzODAzfQ"
    ".eCFcjx7gOhiv7mCyR2RiadndE9d6e6kVOWysHrarZTM"
)

_DEFAULT_COUNTRY = "SG"
_ALLOWED_COUNTRIES = frozenset({"SG", "MN", "UY"})
_raw_client_cache: Any = None


def _normalize_country(country: str | None = None) -> str:
    code = str(country or _DEFAULT_COUNTRY).upper()
    if code not in _ALLOWED_COUNTRIES:
        allowed = ", ".join(sorted(_ALLOWED_COUNTRIES))
        raise ValueError(f"Unsupported country code: {code}. Allowed: {allowed}")
    return code


def _get_raw_client() -> Any:
    global _raw_client_cache
    if _raw_client_cache is None:
        from supabase import create_client

        url = os.environ.get("SUPABASE_URL", _DEFAULT_URL)
        key = os.environ.get("SUPABASE_KEY", _DEFAULT_KEY)
        _raw_client_cache = create_client(url, key)
    return _raw_client_cache


def get_client() -> Any:
    return _get_raw_client()


def get_mn_client() -> Any:
    return _get_raw_client()


get_supabase_client = get_client


def fetch_all_products(country: str = _DEFAULT_COUNTRY) -> list[dict[str, Any]]:
    code = _normalize_country(country)
    sb = get_client()
    result = (
        sb.table("products")
        .select("*")
        .eq("country", code)
        .is_("deleted_at", "null")
        .order("crawled_at", desc=True)
        .execute()
    )
    return result.data or []


def fetch_kup_products(country: str = _DEFAULT_COUNTRY) -> list[dict[str, Any]]:
    code = _normalize_country(country)
    sb = get_client()
    result = (
        sb.table("products")
        .select("*")
        .eq("country", code)
        .eq("source_name", f"{code}:kup_pipeline")
        .is_("deleted_at", "null")
        .execute()
    )
    return result.data or []


def upsert_product(row: dict[str, Any]) -> bool:
    sb = get_client()
    now = datetime.now(timezone.utc).isoformat()
    payload = dict(row)
    payload["country"] = _normalize_country(payload.get("country"))
    payload.setdefault("crawled_at", now)
    payload.setdefault("confidence", 0.5)
    try:
        sb.table("products").upsert(
            payload,
            on_conflict="country,source_name,source_url",
        ).execute()
        return True
    except Exception:
        return False
