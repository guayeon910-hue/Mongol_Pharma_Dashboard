"""Supabase 클라이언트 -MN(몽골) 전용 격리 래퍼 포함.

팀 공유 DB에서 MN 작업이 다른 국가(SG·UY 등) 데이터를 건드리지 않도록
MnSafeClient가 모든 테이블 접근을 허가 목록 기준으로 차단한다.

허가 목록:
  mn_*  접두 테이블  -전체 CRUD 허용 (MN 전용이므로 별도 필터 불필요)
  products (공유)    -SELECT/INSERT/UPSERT 시 country="MN" 자동 주입,
                       UPDATE data에 country 변조 시 차단,
                       DELETE 시 country="MN" 조건 자동 추가

그 외 테이블(sg_*, uy_* 등) -PermissionError 즉시 발생

환경변수:
  SUPABASE_URL  (없으면 하드코딩 기본값)
  SUPABASE_KEY  (없으면 하드코딩 기본값)
"""

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

# ── 허가 테이블 목록 ──────────────────────────────────────────────────────────

_MN_OWN_TABLES: frozenset[str] = frozenset({
    "mn_pricing",
    "mn_licemed_registry",
    "mn_tender_awards",
    "mn_partner_scores",
    "mn_mmra_notices",
})

# country 컬럼으로 행을 구분하는 팀 공유 테이블
_SHARED_COUNTRY_TABLES: frozenset[str] = frozenset({
    "products",
})

_COUNTRY_CODE = "MN"

# ── 격리 래퍼 ─────────────────────────────────────────────────────────────────


class _MnTableProxy:
    """단일 테이블에 대한 격리 프록시.

    - MN 전용 테이블(mn_*): 접근 허용, 필터 주입 없음
    - 공유 테이블(products 등): country="MN" 자동 주입
    - 기타 모든 테이블: PermissionError
    """

    def __init__(self, raw_client: Any, table_name: str) -> None:
        if table_name not in _MN_OWN_TABLES and table_name not in _SHARED_COUNTRY_TABLES:
            raise PermissionError(
                f"[MN 격리 차단] '{table_name}' 테이블에 접근할 수 없습니다. "
                f"mn_* 전용 테이블 또는 허가된 공유 테이블만 사용 가능합니다. "
                f"(다른 국가 데이터 보호)"
            )
        self._qb = raw_client.table(table_name)
        self._shared = table_name in _SHARED_COUNTRY_TABLES

    # ── SELECT ──────────────────────────────────────────────────────────────

    def select(self, columns: str = "*", **kwargs: Any) -> Any:
        qb = self._qb.select(columns, **kwargs)
        if self._shared:
            qb = qb.eq("country", _COUNTRY_CODE)
        return qb

    # ── INSERT ──────────────────────────────────────────────────────────────

    def insert(self, data: Any, **kwargs: Any) -> Any:
        if self._shared:
            data = _stamp_country(data)
        return self._qb.insert(data, **kwargs)

    # ── UPSERT ──────────────────────────────────────────────────────────────

    def upsert(self, data: Any, **kwargs: Any) -> Any:
        if self._shared:
            data = _stamp_country(data)
        return self._qb.upsert(data, **kwargs)

    # ── UPDATE ──────────────────────────────────────────────────────────────

    def update(self, data: Any, **kwargs: Any) -> Any:
        if self._shared:
            if isinstance(data, dict):
                c = data.get("country")
                if c is not None and c != _COUNTRY_CODE:
                    raise PermissionError(
                        f"[MN 격리 차단] UPDATE로 country='{c}' 변조 시도 차단 -"
                        f"MN 전용 데이터만 수정 가능합니다."
                    )
                # 실수로 country 누락 시 자동 보정
                data = {**data, "country": _COUNTRY_CODE}
        return self._qb.update(data, **kwargs)

    # ── DELETE ──────────────────────────────────────────────────────────────

    def delete(self) -> Any:
        qb = self._qb.delete()
        if self._shared:
            # 공유 테이블 DELETE는 country="MN" 조건 자동 추가
            qb = qb.eq("country", _COUNTRY_CODE)
        return qb

    # ── 기타 QueryBuilder 메서드 패스스루 ──────────────────────────────────

    def __getattr__(self, name: str) -> Any:
        return getattr(self._qb, name)


def _stamp_country(data: Any) -> Any:
    """INSERT/UPSERT 데이터에 country="MN" 강제 설정.

    타국 country 값이 있으면 즉시 PermissionError 발생.
    """
    if isinstance(data, list):
        return [_stamp_single(row) for row in data]
    return _stamp_single(data)


def _stamp_single(row: Any) -> Any:
    if not isinstance(row, dict):
        return row
    c = row.get("country")
    if c is not None and c != _COUNTRY_CODE:
        raise PermissionError(
            f"[MN 격리 차단] country='{c}' 행 삽입 시도 차단 -"
            f"이 코드베이스는 MN 데이터만 기록할 수 있습니다."
        )
    return {**row, "country": _COUNTRY_CODE}


class MnSafeClient:
    """Supabase raw 클라이언트를 감싸는 MN 격리 클라이언트.

    사용법:
        sb = get_mn_client()
        sb.table("mn_pricing").insert({...}).execute()   # OK
        sb.table("sg_pricing").insert({...}).execute()   # PermissionError
        sb.table("products").insert({"country": "SG"})   # PermissionError
    """

    def __init__(self, raw_client: Any) -> None:
        self._raw = raw_client

    def table(self, name: str) -> _MnTableProxy:
        return _MnTableProxy(self._raw, name)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._raw, name)


# ── 클라이언트 팩토리 ─────────────────────────────────────────────────────────

_raw_client_cache: Any = None
_mn_client_cache: MnSafeClient | None = None


def _get_raw_client() -> Any:
    global _raw_client_cache
    if _raw_client_cache is None:
        from supabase import create_client
        url = os.environ.get("SUPABASE_URL", _DEFAULT_URL)
        key = os.environ.get("SUPABASE_KEY", _DEFAULT_KEY)
        _raw_client_cache = create_client(url, key)
    return _raw_client_cache


def get_mn_client() -> MnSafeClient:
    """MN 격리 Supabase 클라이언트 싱글톤 반환."""
    global _mn_client_cache
    if _mn_client_cache is None:
        _mn_client_cache = MnSafeClient(_get_raw_client())
    return _mn_client_cache


# 기존 코드 호환성: get_client() / get_supabase_client() 모두 격리 클라이언트 반환
def get_client() -> MnSafeClient:
    return get_mn_client()


get_supabase_client = get_mn_client


# ── 공용 헬퍼 함수 ────────────────────────────────────────────────────────────

def fetch_all_products(country: str = _COUNTRY_CODE) -> list[dict[str, Any]]:
    """products 테이블에서 MN 품목 전체 조회."""
    if country != _COUNTRY_CODE:
        raise PermissionError(f"[MN 격리] country='{country}' 조회 차단")
    sb = get_mn_client()
    r = (
        sb.table("products")
        .select("*")
        .is_("deleted_at", "null")
        .order("crawled_at", desc=True)
        .execute()
    )
    return r.data or []


def fetch_kup_products(country: str = _COUNTRY_CODE) -> list[dict[str, Any]]:
    """KUP 파이프라인 MN 품목 조회."""
    if country != _COUNTRY_CODE:
        raise PermissionError(f"[MN 격리] country='{country}' 조회 차단")
    sb = get_mn_client()
    r = (
        sb.table("products")
        .select("*")
        .eq("source_name", f"{_COUNTRY_CODE}:kup_pipeline")
        .is_("deleted_at", "null")
        .execute()
    )
    return r.data or []


def upsert_product(row: dict[str, Any]) -> bool:
    """products 테이블에 MN 품목 upsert. 실패 시 False 반환."""
    sb = get_mn_client()
    now = datetime.now(timezone.utc).isoformat()
    row = {**row, "country": _COUNTRY_CODE}  # 강제 설정
    row.setdefault("crawled_at", now)
    row.setdefault("confidence", 0.5)
    try:
        sb.table("products").upsert(
            row,
            on_conflict="country,source_name,source_url",
        ).execute()
        return True
    except Exception:
        return False
