"""Synthetic Thai insurance product catalog.

IMPORTANT: all premiums, limits, and returns in this module are illustrative
sample data built to show realistic *relative* pricing patterns (e.g. how a
deductible lowers a health premium, or how whole life cash value builds).
They are NOT live rate-card quotes from any insurer and must not be presented
to a client as an actual quotation. Always re-quote from the insurer / a
licensed agent before advising a purchase.
"""

import pandas as pd

INSURERS = [
    "AIA ประเทศไทย",
    "เมืองไทยประกันชีวิต (MTL)",
    "พรูเด็นเชียล ประเทศไทย",
    "เอฟดับบลิวดี ประกันชีวิต (FWD)",
    "กรุงไทย-แอกซ่า ประกันชีวิต",
    "อลิอันซ์ อยุธยา ประกันชีวิต",
    "ไทยประกันชีวิต",
    "กรุงเทพประกันชีวิต",
]

# age-band premium multipliers, baseline = age 31-40 (index tier used for all
# "base" premiums stored in the catalog below)
AGE_BANDS = [
    ("18-30", 18, 30, 0.72),
    ("31-40", 31, 40, 1.00),
    ("41-50", 41, 50, 1.55),
    ("51-60", 51, 60, 2.35),
    ("61-70", 61, 70, 3.80),
    ("71-80", 71, 80, 6.20),
]


def age_multiplier(age: int) -> float:
    for _, lo, hi, mult in AGE_BANDS:
        if lo <= age <= hi:
            return mult
    if age < AGE_BANDS[0][1]:
        return AGE_BANDS[0][3]
    return AGE_BANDS[-1][3]


def age_band_label(age: int) -> str:
    for label, lo, hi, _ in AGE_BANDS:
        if lo <= age <= hi:
            return label
    return "60+" if age > 60 else "<18"


# Sex-based premium loading, baseline = female (1.00) for each category.
# Grounded in the two real patterns actually seen in Thai retail pricing:
# life/investment carry a mortality-risk loading for males (level term and
# whole life price higher for men because of shorter statistical life
# expectancy), while health plans commonly price women slightly higher
# because of maternity-related utilisation. Retirement/annuity products in
# this sample are unisex-priced -- Thai guaranteed-annuity retail products are
# typically not medically underwritten by sex, so no loading is applied there.
# These are illustrative loadings for a *relative* pricing pattern, same
# caveat as the rest of data.py: not a real insurer's actual rate table.
SEX_LABELS = {"male": "ชาย", "female": "หญิง"}
SEX_MULTIPLIER = {
    "health": {"male": 1.00, "female": 1.05},
    "investment": {"male": 1.06, "female": 1.00},
    "life": {"male": 1.12, "female": 1.00},
    "retirement": {"male": 1.00, "female": 1.00},
}


def sex_multiplier(category: str, sex: str | None) -> float:
    if sex not in ("male", "female"):
        return 1.0
    return SEX_MULTIPLIER.get(category, {}).get(sex, 1.0)


# ---------------------------------------------------------------------------
# HEALTH — each base plan is offered at four deductible tiers. The deductible
# is the amount the client pays out of pocket per policy year before the
# health plan starts paying; insurers discount the premium for taking it on.
# ---------------------------------------------------------------------------
DEDUCTIBLE_TIERS = [0, 30_000, 50_000, 100_000]
# empirical-style discount curve vs the 0-deductible premium
_DEDUCTIBLE_DISCOUNT = {0: 1.00, 30_000: 0.72, 50_000: 0.60, 100_000: 0.42}

_HEALTH_BASE = [
    # insurer, product_name, base_premium_age31_40 (deductible=0), ipd_limit, room_rate, opd_limit_per_visit, opd_visits_yr, day_surgery, entry_age_max, renew_to_age
    ("AIA ประเทศไทย", "AIA H&S (Health Happy)", 46_000, 5_000_000, 6_000, 2_000, 30, True, 65, 99),
    ("เมืองไทยประกันชีวิต (MTL)", "MTL Extra Care", 42_500, 5_000_000, 5_000, 1_800, 30, True, 65, 99),
    ("พรูเด็นเชียล ประเทศไทย", "PRUExtra Care (Elite)", 51_000, 20_000_000, 8_000, 2_500, 30, True, 60, 99),
    ("เอฟดับบลิวดี ประกันชีวิต (FWD)", "FWD Health Cancer Plus", 38_000, 5_000_000, 5_000, 0, 0, True, 65, 84),
    ("กรุงไทย-แอกซ่า ประกันชีวิต", "iHealthy Ultra", 44_000, 5_000_000, 6_000, 2_000, 30, True, 65, 98),
    ("อลิอันซ์ อยุธยา ประกันชีวิต", "Health Saver", 36_500, 3_000_000, 4_000, 1_500, 25, True, 60, 90),
    ("ไทยประกันชีวิต", "Thai Life Health Premier", 40_000, 5_000_000, 5_000, 1_800, 30, True, 65, 99),
    ("กรุงเทพประกันชีวิต", "BLA Health Class", 39_000, 4_000_000, 5_000, 1_500, 25, False, 60, 90),
]


def _build_health_rows():
    rows = []
    for (insurer, name, base_prem, ipd, room, opd_limit, opd_visits,
         day_surgery, entry_max, renew_to) in _HEALTH_BASE:
        for ded in DEDUCTIBLE_TIERS:
            rows.append(dict(
                category="health",
                insurer=insurer,
                product_name=name,
                deductible_thb=ded,
                annual_premium_base=round(base_prem * _DEDUCTIBLE_DISCOUNT[ded], -2),
                ipd_annual_limit=ipd,
                room_rate_per_day=room,
                opd_limit_per_visit=opd_limit,
                opd_visits_per_year=opd_visits,
                day_surgery_covered=day_surgery,
                entry_age_max=entry_max,
                renewable_to_age=renew_to,
                waiting_period_days=30,
            ))
    return rows


HEALTH_PRODUCTS = _build_health_rows()

# ---------------------------------------------------------------------------
# INVESTMENT-LINKED (unit-linked)
# ---------------------------------------------------------------------------
INVESTMENT_PRODUCTS = [
    dict(category="investment", insurer="AIA ประเทศไทย", product_name="AIA Issara Legacy (ILP)",
         min_annual_premium=60_000, life_coverage_multiple=15, fund_choices_count=25,
         avg_fund_mgmt_fee_pct=1.5, avg_annual_return_5y_pct=6.2, surrender_charge_years=5, risk_level=3),
    dict(category="investment", insurer="เมืองไทยประกันชีวิต (MTL)", product_name="MTL Smart Wealth (ILP)",
         min_annual_premium=50_000, life_coverage_multiple=10, fund_choices_count=20,
         avg_fund_mgmt_fee_pct=1.6, avg_annual_return_5y_pct=5.8, surrender_charge_years=5, risk_level=3),
    dict(category="investment", insurer="พรูเด็นเชียล ประเทศไทย", product_name="PRUWealth Legacy (ILP)",
         min_annual_premium=80_000, life_coverage_multiple=20, fund_choices_count=30,
         avg_fund_mgmt_fee_pct=1.4, avg_annual_return_5y_pct=6.8, surrender_charge_years=6, risk_level=4),
    dict(category="investment", insurer="เอฟดับบลิวดี ประกันชีวิต (FWD)", product_name="FWD Invest First (ILP)",
         min_annual_premium=40_000, life_coverage_multiple=8, fund_choices_count=15,
         avg_fund_mgmt_fee_pct=1.7, avg_annual_return_5y_pct=5.4, surrender_charge_years=4, risk_level=2),
    dict(category="investment", insurer="กรุงไทย-แอกซ่า ประกันชีวิต", product_name="Krungthai-AXA iWealthy (ILP)",
         min_annual_premium=100_000, life_coverage_multiple=25, fund_choices_count=35,
         avg_fund_mgmt_fee_pct=1.3, avg_annual_return_5y_pct=7.1, surrender_charge_years=6, risk_level=4),
    dict(category="investment", insurer="อลิอันซ์ อยุธยา ประกันชีวิต", product_name="Allianz Ayudhya Invest Link",
         min_annual_premium=45_000, life_coverage_multiple=10, fund_choices_count=18,
         avg_fund_mgmt_fee_pct=1.6, avg_annual_return_5y_pct=5.6, surrender_charge_years=5, risk_level=3),
]

# ---------------------------------------------------------------------------
# LIFE (whole life + term)
# ---------------------------------------------------------------------------
LIFE_PRODUCTS = [
    dict(category="life", insurer="AIA ประเทศไทย", product_name="AIA 20 Pay Life",
         life_type="Whole Life", sum_assured=1_000_000, annual_premium_base=32_000,
         premium_payment_years=20, coverage_to_age=99, cash_value_pct_at_year20=118),
    dict(category="life", insurer="เมืองไทยประกันชีวิต (MTL)", product_name="MTL Life Legacy 99/20",
         life_type="Whole Life", sum_assured=1_000_000, annual_premium_base=29_500,
         premium_payment_years=20, coverage_to_age=99, cash_value_pct_at_year20=112),
    dict(category="life", insurer="ไทยประกันชีวิต", product_name="Thai Life 99/20",
         life_type="Whole Life", sum_assured=1_000_000, annual_premium_base=30_500,
         premium_payment_years=20, coverage_to_age=99, cash_value_pct_at_year20=115),
    dict(category="life", insurer="กรุงเทพประกันชีวิต", product_name="BLA Whole Life 90/20",
         life_type="Whole Life", sum_assured=1_000_000, annual_premium_base=28_800,
         premium_payment_years=20, coverage_to_age=90, cash_value_pct_at_year20=108),
    dict(category="life", insurer="เอฟดับบลิวดี ประกันชีวิต (FWD)", product_name="FWD Term 20 Protect",
         life_type="Term Life", sum_assured=2_000_000, annual_premium_base=8_200,
         premium_payment_years=20, coverage_to_age=60, cash_value_pct_at_year20=0),
    dict(category="life", insurer="กรุงไทย-แอกซ่า ประกันชีวิต", product_name="Krungthai-AXA Term Care",
         life_type="Term Life", sum_assured=2_000_000, annual_premium_base=7_600,
         premium_payment_years=15, coverage_to_age=65, cash_value_pct_at_year20=0),
    dict(category="life", insurer="อลิอันซ์ อยุธยา ประกันชีวิต", product_name="Allianz Ayudhya i-Term",
         life_type="Term Life", sum_assured=2_000_000, annual_premium_base=8_600,
         premium_payment_years=20, coverage_to_age=70, cash_value_pct_at_year20=0),
    dict(category="life", insurer="พรูเด็นเชียล ประเทศไทย", product_name="Prudential PRUProtector 99/20",
         life_type="Whole Life", sum_assured=1_000_000, annual_premium_base=33_500,
         premium_payment_years=20, coverage_to_age=99, cash_value_pct_at_year20=120),
]

# ---------------------------------------------------------------------------
# RETIREMENT / ANNUITY (ประกันบำนาญ)
# ---------------------------------------------------------------------------
RETIREMENT_PRODUCTS = [
    dict(category="retirement", insurer="เมืองไทยประกันชีวิต (MTL)", product_name="MTL Annuity 90/60",
         sum_assured=1_000_000, annual_premium_base=45_000, premium_payment_years=15,
         payout_start_age=60, payout_end_age=90, guaranteed_annual_payout_pct=15.0,
         estimated_irr_pct=2.1),
    dict(category="retirement", insurer="AIA ประเทศไทย", product_name="AIA Annuity Fix 85/60",
         sum_assured=1_000_000, annual_premium_base=48_000, premium_payment_years=15,
         payout_start_age=60, payout_end_age=85, guaranteed_annual_payout_pct=18.0,
         estimated_irr_pct=1.8),
    dict(category="retirement", insurer="ไทยประกันชีวิต", product_name="Thai Life Annuity 88/60",
         sum_assured=1_000_000, annual_premium_base=46_500, premium_payment_years=15,
         payout_start_age=60, payout_end_age=88, guaranteed_annual_payout_pct=16.0,
         estimated_irr_pct=1.9),
    dict(category="retirement", insurer="กรุงไทย-แอกซ่า ประกันชีวิต", product_name="Krungthai-AXA Retire Fit 85/55",
         sum_assured=1_000_000, annual_premium_base=52_000, premium_payment_years=10,
         payout_start_age=55, payout_end_age=85, guaranteed_annual_payout_pct=17.0,
         estimated_irr_pct=1.7),
    dict(category="retirement", insurer="กรุงเทพประกันชีวิต", product_name="BLA Annuity Rich 88/60",
         sum_assured=1_000_000, annual_premium_base=44_000, premium_payment_years=15,
         payout_start_age=60, payout_end_age=88, guaranteed_annual_payout_pct=15.5,
         estimated_irr_pct=2.0),
    dict(category="retirement", insurer="อลิอันซ์ อยุธยา ประกันชีวิต", product_name="Allianz Ayudhya Annuity 90/55",
         sum_assured=1_000_000, annual_premium_base=50_000, premium_payment_years=12,
         payout_start_age=55, payout_end_age=90, guaranteed_annual_payout_pct=14.5,
         estimated_irr_pct=1.9),
]

ALL_PRODUCTS = HEALTH_PRODUCTS + INVESTMENT_PRODUCTS + LIFE_PRODUCTS + RETIREMENT_PRODUCTS


def products_df() -> pd.DataFrame:
    return pd.DataFrame(ALL_PRODUCTS)


def health_df(age: int | None = None, sex: str | None = None) -> pd.DataFrame:
    df = pd.DataFrame(HEALTH_PRODUCTS).copy()
    mult = (age_multiplier(age) if age is not None else 1.0) * sex_multiplier("health", sex)
    df["annual_premium"] = (df["annual_premium_base"] * mult).round(-2)
    return df


def investment_df(sex: str | None = None) -> pd.DataFrame:
    df = pd.DataFrame(INVESTMENT_PRODUCTS).copy()
    mult = sex_multiplier("investment", sex)
    df["min_annual_premium"] = (df["min_annual_premium"] * mult).round(-2)
    return df


def life_df(age: int | None = None, sex: str | None = None) -> pd.DataFrame:
    df = pd.DataFrame(LIFE_PRODUCTS).copy()
    mult = (age_multiplier(age) if age is not None else 1.0) * sex_multiplier("life", sex)
    df["annual_premium"] = (df["annual_premium_base"] * mult).round(-2)
    return df


def retirement_df(age: int | None = None, sex: str | None = None) -> pd.DataFrame:
    df = pd.DataFrame(RETIREMENT_PRODUCTS).copy()
    mult = (age_multiplier(age) if age is not None else 1.0) * sex_multiplier("retirement", sex)
    df["annual_premium"] = (df["annual_premium_base"] * mult).round(-2)
    return df
