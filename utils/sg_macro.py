"""Stable macro cards for the Singapore dashboard."""

from __future__ import annotations

from typing import Any

_SG_MACRO_CARDS: list[dict[str, str]] = [
    {"label": "1인당 GDP", "value": "US$ 88,447", "sub": "IMF"},
    {"label": "인구", "value": "5,917,600명", "sub": "Singstat"},
    {"label": "의약품 시장 규모", "value": "$4.8B", "sub": "IQVIA"},
    {"label": "의약품 국가 수입 의존도", "value": "~85%", "sub": "HSA"},
]


def get_sg_macro_cards() -> list[dict[str, Any]]:
    return list(_SG_MACRO_CARDS)


def get_sg_macro() -> list[dict[str, Any]]:
    return get_sg_macro_cards()


SG_MACRO = _SG_MACRO_CARDS
