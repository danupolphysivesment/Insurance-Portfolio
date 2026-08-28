"""Thai insurance product catalog.

Product names, coverage limits, room rates, deductible availability, payment
periods, coverage-to-age, and payout percentages below are checked against
each insurer's own official website (research pass 2026-08-28, via each
insurer's own domain — aia.co.th, muangthai.co.th, prudential.co.th, fwd.co.th,
krungthai-axa.co.th, azay.co.th, thailife.com/product.thailife.com,
bangkoklife.com). Where a product genuinely doesn't exist in the market (e.g.
Thai Life has no true unit-linked product, only Universal Life; Krungthai-AXA,
Thai Life and Bangkok Life have no standalone term-life product), it is
deliberately left out rather than invented -- see the per-section notes below.

PREMIUMS remain illustrative sample numbers. No Thai insurer publishes a
public age/gender premium table; real premiums need an underwritten quote.
Where an insurer's own page showed a concrete premium example, the number
here was calibrated against it, but this is NOT a live rate-card quote and
must not be presented to a client as an actual quotation. Always re-quote
from the insurer / a licensed agent before advising a purchase.
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
# HEALTH
# ---------------------------------------------------------------------------
# Anchor points for how much a deductible discounts the zero-deductible
# premium, interpolated so any real deductible amount an insurer actually
# offers (not just a fixed 30k/50k/100k list) gets a sensible multiplier.
_DEFAULT_DEDUCTIBLE_TIERS = [0, 30_000, 50_000, 100_000]
_DED_ANCHORS = [(0, 1.00), (30_000, 0.72), (50_000, 0.60), (100_000, 0.42)]


def _deductible_discount(amount: int) -> float:
    xs = [a for a, _ in _DED_ANCHORS]
    ys = [d for _, d in _DED_ANCHORS]
    if amount <= xs[0]:
        return ys[0]
    if amount >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if xs[i] <= amount <= xs[i + 1]:
            t = (amount - xs[i]) / (xs[i + 1] - xs[i])
            return ys[i] + t * (ys[i + 1] - ys[i])
    return 1.0


_HEALTH_BASE = [
    # insurer, product_name, base_premium_age31_40 (deductible=0), ipd_limit, room_rate,
    # opd_limit_per_visit, opd_visits_yr, day_surgery, entry_age_max, renew_to_age, deductible_tiers
    #
    # Real deductible tiers vary by insurer (Prudential: 20k/30k/60k; FWD:
    # 30k/50k; Thai Life: 30k/50k; Bangkok Life: 30k/100k) rather than one
    # universal set -- ded_tiers=None falls back to the standard 4-tier list
    # for insurers whose page confirms "selectable" but not the exact amounts
    # (Krungthai-AXA, MTL D Health Lite/Extra Care Plus).

    # AIA — Health Happy has 4 coverage tiers (1M/5M/15M/25M, no deductible on
    # any); Infinite Care is the separate flagship global plan. Neither offers
    # a deductible option per aia.co.th.
    ("AIA ประเทศไทย", "AIA Health Happy", 52_000, 15_000_000, 6_000, 0, 0, True, 75, 98, [0]),
    ("AIA ประเทศไทย", "AIA Infinite Care", 95_000, 120_000_000, 25_000, 5_000, 20, True, 75, 98, [0]),

    # MTL — 4 real products (checked 2026-08-28 at muangthai.co.th/th/health-insurance):
    # Elite Health Plus and เหมาจ่าย Extra explicitly have no deductible
    # option; D Health Lite and Extra Care Plus are selectable.
    ("เมืองไทยประกันชีวิต (MTL)", "MTL Elite Health Plus", 58_000, 30_000_000, 15_000, 2_500, 30, True, 90, 99, [0]),
    ("เมืองไทยประกันชีวิต (MTL)", "MTL D Health Lite", 34_000, 5_000_000, 4_000, 1_500, 25, True, 90, 99, None),
    ("เมืองไทยประกันชีวิต (MTL)", "MTL เหมาจ่าย Extra (Maochai Extra)", 15_500, 500_000, 3_000, 0, 0, True, 90, 99, [0]),
    ("เมืองไทยประกันชีวิต (MTL)", "MTL Extra Care Plus", 16_000, 500_000, 3_000, 0, 0, True, 90, 99, None),

    # Prudential — PRU Mhao Mhao Double Sure, deductible tiers 20k/30k/60k
    # confirmed on prudential.co.th (plan 2 of 4 shown here).
    ("พรูเด็นเชียล ประเทศไทย", "PRU Mhao Mhao Double Sure", 19_500, 500_000, 2_500, 1_600, 30, True, 65, 99, [0, 20_000, 30_000, 60_000]),

    # FWD — Easy E-Health Standard plan; premium calibrated to a real number
    # this app's own live-pull captured from fwd.co.th (see live_data.py):
    # Basic 12,659 / Standard 24,471 / Advance 35,164 THB/yr, deductible 30k/50k.
    ("เอฟดับบลิวดี ประกันชีวิต (FWD)", "FWD Easy E-Health (Standard)", 24_471, 1_000_000, 3_000, 3_000, 30, True, 60, 80, [0, 30_000, 50_000]),

    # Krungthai-AXA — iHealthy Ultra has 6 real coverage tiers (Smart 3M up to
    # Platinum 100M); Silver (15M) used as representative. Deductible is
    # confirmed selectable but exact tier amounts are brochure-gated, so this
    # falls back to the standard tier list rather than guessing figures.
    ("กรุงไทย-แอกซ่า ประกันชีวิต", "iHealthy Ultra (Silver)", 62_000, 15_000_000, 6_000, 2_000, 30, True, 80, 98, None),

    # Allianz Ayudhya — ปลดล็อค ดับเบิล แคร์ (My Health Plus Double Care),
    # plan 2 of 3; no deductible option for adults per azay.co.th (children
    # under 10 require one, not modeled here).
    ("อลิอันซ์ อยุธยา ประกันชีวิต", "Allianz ปลดล็อค ดับเบิล แคร์ (Double Care)", 54_000, 15_000_000, 6_000, 0, 0, True, 70, 89, [0]),

    # Thai Life — Health เหมาสบายใจสบายตังค์, plan 4 of 5 (5M/30k deductible)
    # confirmed on product.thailife.com.
    ("ไทยประกันชีวิต", "Thai Life เหมาสบายใจสบายตังค์", 38_000, 5_000_000, 3_000, 0, 0, True, 70, 99, [0, 30_000, 50_000]),

    # Bangkok Life — BLA Complete Health, plan 3 of 3 (5M, deductible 30k or
    # 100k) confirmed on bangkoklife.com.
    ("กรุงเทพประกันชีวิต", "BLA Complete Health", 41_000, 5_000_000, 4_000, 0, 0, True, 65, 99, [0, 30_000, 100_000]),
]


def _build_health_rows():
    rows = []
    for (insurer, name, base_prem, ipd, room, opd_limit, opd_visits,
         day_surgery, entry_max, renew_to, ded_tiers) in _HEALTH_BASE:
        for ded in (ded_tiers if ded_tiers is not None else _DEFAULT_DEDUCTIBLE_TIERS):
            rows.append(dict(
                category="health",
                insurer=insurer,
                product_name=name,
                deductible_thb=ded,
                annual_premium_base=round(base_prem * _deductible_discount(ded), -2),
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
# Actual union of deductible amounts across every product above -- not a
# fixed list, since real tiers differ by insurer.
DEDUCTIBLE_TIERS = sorted({r["deductible_thb"] for r in HEALTH_PRODUCTS})

# ---------------------------------------------------------------------------
# INVESTMENT-LINKED (unit-linked / ประกันชีวิตควบการลงทุน)
# ---------------------------------------------------------------------------
# Thai Life is deliberately absent: its "investment" category page markets
# only TL Universal Life (company-managed crediting rate), not a genuine
# customer-selected-fund unit-linked product -- confirmed on thailife.com and
# their own investor-relations FAQ, so it doesn't belong in this comparison.
# min_annual_premium and coverage multiples below use each insurer's stated
# real minimum where the page disclosed one (MTL fund count 54+ is real and
# confirmed multi-AMC; Allianz's 12,000 THB/yr minimum RPP is real); fee %,
# 5yr return %, and surrender years remain illustrative since those aren't
# publicly tabulated.
INVESTMENT_PRODUCTS = [
    dict(category="investment", insurer="AIA ประเทศไทย", product_name="AIA Issara Plus (Unit Linked)",
         min_annual_premium=50_000, life_coverage_multiple=20, fund_choices_count=25,
         avg_fund_mgmt_fee_pct=1.5, avg_annual_return_5y_pct=6.2, surrender_charge_years=5, risk_level=3),
    dict(category="investment", insurer="เมืองไทยประกันชีวิต (MTL)", product_name="MTL mDesign (Unit Linked)",
         min_annual_premium=50_000, life_coverage_multiple=10, fund_choices_count=54,
         avg_fund_mgmt_fee_pct=1.6, avg_annual_return_5y_pct=5.8, surrender_charge_years=5, risk_level=3),
    dict(category="investment", insurer="พรูเด็นเชียล ประเทศไทย", product_name="PRUSuper Link (Unit Linked)",
         min_annual_premium=80_000, life_coverage_multiple=40, fund_choices_count=30,
         avg_fund_mgmt_fee_pct=1.4, avg_annual_return_5y_pct=6.8, surrender_charge_years=6, risk_level=4),
    dict(category="investment", insurer="เอฟดับบลิวดี ประกันชีวิต (FWD)", product_name="FWD Freedom Linked Plus 15/5",
         min_annual_premium=40_000, life_coverage_multiple=25, fund_choices_count=15,
         avg_fund_mgmt_fee_pct=1.7, avg_annual_return_5y_pct=5.4, surrender_charge_years=4, risk_level=2),
    dict(category="investment", insurer="กรุงไทย-แอกซ่า ประกันชีวิต", product_name="Krungthai-AXA iWealthy",
         min_annual_premium=100_000, life_coverage_multiple=30, fund_choices_count=35,
         avg_fund_mgmt_fee_pct=1.3, avg_annual_return_5y_pct=7.1, surrender_charge_years=6, risk_level=4),
    dict(category="investment", insurer="อลิอันซ์ อยุธยา ประกันชีวิต", product_name="Allianz Unit Linked My Style Protect",
         min_annual_premium=12_000, life_coverage_multiple=20, fund_choices_count=18,
         avg_fund_mgmt_fee_pct=1.6, avg_annual_return_5y_pct=5.6, surrender_charge_years=5, risk_level=3),
    dict(category="investment", insurer="กรุงเทพประกันชีวิต", product_name="BLA Premier Link (Unit Linked)",
         min_annual_premium=12_000, life_coverage_multiple=20, fund_choices_count=20,
         avg_fund_mgmt_fee_pct=1.5, avg_annual_return_5y_pct=5.7, surrender_charge_years=5, risk_level=3),
]

# ---------------------------------------------------------------------------
# LIFE (whole life ตลอดชีพ + term ชั่วระยะเวลา)
# ---------------------------------------------------------------------------
# Krungthai-AXA, Thai Life and Bangkok Life deliberately have NO term-life row
# below: none of the three currently markets a standalone term product on
# its official site (confirmed by checking each insurer's full life-insurance
# category listing) -- only whole life / unit-linked whole life. Listing a
# term product for them would be fabricating a product that doesn't exist.
LIFE_PRODUCTS = [
    dict(category="life", insurer="AIA ประเทศไทย", product_name="AIA 20 Pay Life (Non Par)",
         life_type="Whole Life", sum_assured=1_000_000, annual_premium_base=32_000,
         premium_payment_years=20, coverage_to_age=99, cash_value_pct_at_year20=105),
    dict(category="life", insurer="AIA ประเทศไทย", product_name="AIA Term 20",
         life_type="Term Life", sum_assured=2_000_000, annual_premium_base=8_000,
         premium_payment_years=20, coverage_to_age=60, cash_value_pct_at_year20=0),
    dict(category="life", insurer="เมืองไทยประกันชีวิต (MTL)", product_name="MTL สมาร์ท โพรเทคชั่น 99/20",
         life_type="Whole Life", sum_assured=1_000_000, annual_premium_base=29_500,
         premium_payment_years=20, coverage_to_age=99, cash_value_pct_at_year20=112),
    dict(category="life", insurer="เมืองไทยประกันชีวิต (MTL)", product_name="MTL Happy Life Protect 10/10",
         life_type="Term Life", sum_assured=2_000_000, annual_premium_base=4_500,
         premium_payment_years=10, coverage_to_age=45, cash_value_pct_at_year20=0),
    dict(category="life", insurer="พรูเด็นเชียล ประเทศไทย", product_name="PRUWhole Life Protect 99/20",
         life_type="Whole Life", sum_assured=1_000_000, annual_premium_base=33_500,
         premium_payment_years=20, coverage_to_age=99, cash_value_pct_at_year20=120),
    dict(category="life", insurer="พรูเด็นเชียล ประเทศไทย", product_name="PRULife Care (Term 19/19)",
         life_type="Term Life", sum_assured=2_000_000, annual_premium_base=7_300,
         premium_payment_years=19, coverage_to_age=65, cash_value_pct_at_year20=0),
    dict(category="life", insurer="เอฟดับบลิวดี ประกันชีวิต (FWD)", product_name="FWD ไลฟ์ไทม์ รีเทิร์น 99/15",
         life_type="Whole Life", sum_assured=1_000_000, annual_premium_base=31_000,
         premium_payment_years=15, coverage_to_age=99, cash_value_pct_at_year20=110),
    dict(category="life", insurer="เอฟดับบลิวดี ประกันชีวิต (FWD)", product_name="FWD Be Sure (มั่นใจชัวร์)",
         life_type="Term Life", sum_assured=2_000_000, annual_premium_base=7_000,
         premium_payment_years=15, coverage_to_age=55, cash_value_pct_at_year20=0),
    dict(category="life", insurer="กรุงไทย-แอกซ่า ประกันชีวิต", product_name="Krungthai-AXA LifeReady",
         life_type="Whole Life", sum_assured=1_000_000, annual_premium_base=31_000,
         premium_payment_years=18, coverage_to_age=99, cash_value_pct_at_year20=113),
    dict(category="life", insurer="อลิอันซ์ อยุธยา ประกันชีวิต", product_name="Allianz My Whole Life A99/20",
         life_type="Whole Life", sum_assured=1_000_000, annual_premium_base=31_500,
         premium_payment_years=20, coverage_to_age=99, cash_value_pct_at_year20=114),
    dict(category="life", insurer="อลิอันซ์ อยุธยา ประกันชีวิต", product_name="Allianz Ayudhya Term 10/10",
         life_type="Term Life", sum_assured=2_000_000, annual_premium_base=5_000,
         premium_payment_years=10, coverage_to_age=45, cash_value_pct_at_year20=0),
    dict(category="life", insurer="ไทยประกันชีวิต", product_name="Thai Life คุ้มธนกิจ 99/20",
         life_type="Whole Life", sum_assured=1_000_000, annual_premium_base=30_500,
         premium_payment_years=20, coverage_to_age=99, cash_value_pct_at_year20=115),
    dict(category="life", insurer="กรุงเทพประกันชีวิต", product_name="BLA ตลอดชีพ สุดคุ้ม",
         life_type="Whole Life", sum_assured=1_000_000, annual_premium_base=28_800,
         premium_payment_years=20, coverage_to_age=99, cash_value_pct_at_year20=108),
]

# ---------------------------------------------------------------------------
# RETIREMENT / ANNUITY (ประกันบำนาญ)
# ---------------------------------------------------------------------------
RETIREMENT_PRODUCTS = [
    dict(category="retirement", insurer="AIA ประเทศไทย", product_name="AIA Annuity Sure",
         sum_assured=1_000_000, annual_premium_base=48_000, premium_payment_years=9,
         payout_start_age=60, payout_end_age=90, guaranteed_annual_payout_pct=15.0,
         estimated_irr_pct=1.8),
    dict(category="retirement", insurer="เมืองไทยประกันชีวิต (MTL)", product_name="MTL เฟล็กซี่ รีไทร์ 90/5",
         sum_assured=1_000_000, annual_premium_base=45_000, premium_payment_years=15,
         payout_start_age=60, payout_end_age=90, guaranteed_annual_payout_pct=18.0,
         estimated_irr_pct=2.1),
    dict(category="retirement", insurer="พรูเด็นเชียล ประเทศไทย", product_name="PRU Happy Retirement",
         sum_assured=1_000_000, annual_premium_base=47_000, premium_payment_years=15,
         payout_start_age=60, payout_end_age=85, guaranteed_annual_payout_pct=15.0,
         estimated_irr_pct=1.9),
    dict(category="retirement", insurer="เอฟดับบลิวดี ประกันชีวิต (FWD)", product_name="FWD Smart E-Retire 85/60",
         sum_assured=1_000_000, annual_premium_base=53_000, premium_payment_years=20,
         payout_start_age=60, payout_end_age=85, guaranteed_annual_payout_pct=20.0,
         estimated_irr_pct=2.3),
    dict(category="retirement", insurer="เอฟดับบลิวดี ประกันชีวิต (FWD)", product_name="FWD Easy E-Retire 90/5",
         sum_assured=1_000_000, annual_premium_base=60_000, premium_payment_years=5,
         payout_start_age=60, payout_end_age=90, guaranteed_annual_payout_pct=22.0,
         estimated_irr_pct=2.4),
    dict(category="retirement", insurer="กรุงไทย-แอกซ่า ประกันชีวิต", product_name="Krungthai-AXA RetireReady 85/6",
         sum_assured=1_000_000, annual_premium_base=58_000, premium_payment_years=6,
         payout_start_age=60, payout_end_age=85, guaranteed_annual_payout_pct=18.0,
         estimated_irr_pct=2.0),
    dict(category="retirement", insurer="กรุงไทย-แอกซ่า ประกันชีวิต", product_name="Krungthai-AXA Bumnan Smart 95",
         sum_assured=1_000_000, annual_premium_base=62_000, premium_payment_years=6,
         payout_start_age=60, payout_end_age=95, guaranteed_annual_payout_pct=22.0,
         estimated_irr_pct=2.2),
    dict(category="retirement", insurer="อลิอันซ์ อยุธยา ประกันชีวิต", product_name="Allianz My Annuity Plus",
         sum_assured=1_000_000, annual_premium_base=50_000, premium_payment_years=20,
         payout_start_age=55, payout_end_age=85, guaranteed_annual_payout_pct=10.0,
         estimated_irr_pct=1.6),
    dict(category="retirement", insurer="ไทยประกันชีวิต", product_name="Thai Life เศรษฐีรีไทร์ 4 เด้ง",
         sum_assured=1_000_000, annual_premium_base=46_500, premium_payment_years=15,
         payout_start_age=60, payout_end_age=90, guaranteed_annual_payout_pct=15.0,
         estimated_irr_pct=2.0),
    dict(category="retirement", insurer="กรุงเทพประกันชีวิต", product_name="BLA Happy Pension",
         sum_assured=1_000_000, annual_premium_base=44_000, premium_payment_years=10,
         payout_start_age=60, payout_end_age=99, guaranteed_annual_payout_pct=20.0,
         estimated_irr_pct=2.0),
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
