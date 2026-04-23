from __future__ import annotations


def test_cphi_search_config_accepts_mn_product_keys() -> None:
    from utils.cphi_crawler import get_product_search_conf

    conf = get_product_search_conf("MN_sereterol_activair")

    assert "Fluticasone" in conf["ingredients"]
    assert "Salmeterol" in conf["ingredients"]


def test_rank_companies_returns_frontend_fields() -> None:
    from analysis.buyer_scorer import rank_companies

    candidates = [
        {
            "company_name": "Matched Co",
            "ingredient_match": True,
            "enriched": {
                "has_target_country_presence": True,
                "company_overview_kr": "overview",
                "recommendation_reason": "reason",
            },
            "website": "https://example.com",
        },
        {
            "company_name": "Supplement Co",
            "ingredient_match": False,
            "enriched": {},
        },
    ]

    ranked = rank_companies(candidates, top_n=2)

    assert ranked[0]["company_name"] == "Matched Co"
    assert ranked[0]["priority"] == 1
    assert ranked[0]["composite_score"] > ranked[1]["composite_score"]
    assert "scores" in ranked[0]


def test_rank_companies_ignores_unknown_criteria() -> None:
    from analysis.buyer_scorer import rank_companies

    ranked = rank_companies(
        [
            {
                "company_name": "Candidate",
                "ingredient_match": True,
                "enriched": {"has_target_country_presence": True},
            }
        ],
        active_criteria=["on"],
        top_n=1,
    )

    assert ranked[0]["company_name"] == "Candidate"
    assert ranked[0]["composite_score"] > 0
