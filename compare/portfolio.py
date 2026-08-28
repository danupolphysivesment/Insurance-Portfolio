"""Client insurance portfolio: session-state store + gap-analysis summary."""

import streamlit as st

STATE_KEY = "mtl_portfolio_policies"


def init_state():
    if STATE_KEY not in st.session_state:
        st.session_state[STATE_KEY] = []


def add_policy(policy: dict):
    init_state()
    policy = dict(policy)
    policy["id"] = len(st.session_state[STATE_KEY])
    st.session_state[STATE_KEY].append(policy)


def remove_policy(idx: int):
    init_state()
    st.session_state[STATE_KEY] = [
        p for i, p in enumerate(st.session_state[STATE_KEY]) if i != idx
    ]
    for i, p in enumerate(st.session_state[STATE_KEY]):
        p["id"] = i


def get_policies(kinds=("existing", "simulated")) -> list[dict]:
    init_state()
    return [p for p in st.session_state[STATE_KEY] if p.get("kind") in kinds]


def clear_simulated():
    init_state()
    st.session_state[STATE_KEY] = [
        p for p in st.session_state[STATE_KEY] if p.get("kind") != "simulated"
    ]


LIFE_REPLACEMENT_MULTIPLE = 10  # rule of thumb: 10x annual income
HEALTH_COVERAGE_BENCHMARK = 3_000_000  # typical serious-illness IPD cost benchmark
RETIREMENT_INCOME_TARGET_PCT = 0.70  # target 70% of pre-retirement income/yr


def summarize(policies: list[dict], annual_income: float | None = None) -> dict:
    total_premium = sum(p.get("annual_premium", 0) for p in policies)

    by_category = {}
    for p in policies:
        cat = p.get("category", "other")
        by_category.setdefault(cat, {"premium": 0.0, "count": 0, "coverage": 0.0})
        by_category[cat]["premium"] += p.get("annual_premium", 0)
        by_category[cat]["count"] += 1
        by_category[cat]["coverage"] += p.get("coverage_value", 0) or 0

    health_coverage = by_category.get("health", {}).get("coverage", 0.0)
    life_coverage = by_category.get("life", {}).get("coverage", 0.0)
    retirement_annual_payout = sum(
        p.get("annual_payout", 0) for p in policies if p.get("category") == "retirement"
    )

    life_target = (annual_income or 0) * LIFE_REPLACEMENT_MULTIPLE
    life_gap = max(life_target - life_coverage, 0.0)

    health_gap = max(HEALTH_COVERAGE_BENCHMARK - health_coverage, 0.0)

    retirement_target = (annual_income or 0) * RETIREMENT_INCOME_TARGET_PCT
    retirement_gap = max(retirement_target - retirement_annual_payout, 0.0)

    return dict(
        total_premium=total_premium,
        by_category=by_category,
        health_coverage=health_coverage,
        health_gap=health_gap,
        life_coverage=life_coverage,
        life_target=life_target,
        life_gap=life_gap,
        retirement_annual_payout=retirement_annual_payout,
        retirement_target=retirement_target,
        retirement_gap=retirement_gap,
    )
