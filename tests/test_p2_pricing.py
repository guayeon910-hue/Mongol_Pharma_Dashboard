from __future__ import annotations


def test_p2_price_normalization_prefers_mnt() -> None:
    from frontend.server import _normalize_p2_extracted_price

    rates = {"usd_mnt": 3450.0, "mnt_krw": 0.4037}
    out = _normalize_p2_extracted_price(
        {"ref_price_mnt": 8.95, "ref_price_currency": "USD", "ref_price_text": "8.95 USD"},
        "보고서 가격 31,991 MNT · 8.95 USD",
        rates,
    )

    assert out["ref_price_currency"] == "MNT"
    assert out["ref_price_mnt"] == 31991
    assert out["price_basis_currency"] == "MNT"


def test_p2_deterministic_analysis_is_stable() -> None:
    from frontend.server import _build_p2_price_analysis

    rates = {"usd_mnt": 3450.0, "mnt_krw": 0.4037, "mnt_usd": 0.00029}
    extracted = {"ref_price_mnt": 38800}
    first = _build_p2_price_analysis(extracted, rates, "public")
    second = _build_p2_price_analysis(extracted, rates, "public")

    assert first == second
    assert first["scenarios"][0]["base_mnt"] == 38800
    assert first["scenarios"][0]["fee_pct"] == 3.0
    assert first["scenarios"][0]["freight_multiplier"] == 0.85
    assert first["scenarios"][0]["price_mnt"] == 31991
