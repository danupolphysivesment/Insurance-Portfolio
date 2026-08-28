"""Health-deductible offset analysis.

Core idea: a "deductible" health plan is cheaper because the client pays the
first N baht of each policy year's claim out of pocket before the plan pays.
If the client already holds an old health policy (personal or employer group
health) whose remaining annual coverage is large enough to absorb that
deductible, the deductible is no longer a real out-of-pocket risk -- so the
client can safely buy the cheaper deductible variant of a new plan instead of
paying full price for a zero-deductible plan.
"""

from dataclasses import dataclass


@dataclass
class OffsetResult:
    deductible: int
    old_coverage: int
    covered_amount: int
    gap_amount: int
    fully_covered: bool
    savings_vs_zero_deductible: float
    verdict: str  # "recommend" | "caution" | "not_recommended"
    headline: str
    detail: str


def analyze_offset(
    deductible: int,
    old_coverage: int,
    premium_at_deductible: float,
    premium_at_zero_deductible: float,
) -> OffsetResult:
    """Check whether an old policy's coverage can absorb a new plan's deductible.

    old_coverage: the remaining annual claimable amount on the client's
        existing health policy (e.g. IPD annual limit not yet used this
        policy year, or an employer group-health IPD limit).
    """
    covered_amount = min(deductible, max(old_coverage, 0))
    gap_amount = max(deductible - old_coverage, 0)
    fully_covered = gap_amount == 0 and deductible > 0
    savings = max(premium_at_zero_deductible - premium_at_deductible, 0.0)

    if deductible == 0:
        verdict = "not_recommended"
        headline = "แผนนี้ไม่มี Deductible อยู่แล้ว"
        detail = "เบี้ยเต็มราคาแต่ไม่มีความเสี่ยงต้องจ่ายส่วนแรกเอง"
    elif fully_covered:
        verdict = "recommend"
        headline = f"กรมธรรม์เดิมครอบคลุม Deductible ได้เต็มจำนวน {deductible:,.0f} บาท"
        detail = (
            f"วงเงินคงเหลือของกรมธรรม์เดิม ({old_coverage:,.0f} บาท) "
            f"มากกว่าหรือเท่ากับ Deductible ของแผนใหม่ ดังนั้นเมื่อเข้ารักษาตัว "
            f"กรมธรรม์เดิมจะจ่ายส่วนแรกแทนลูกค้าได้ทั้งหมด ทำให้ไม่มีภาระ "
            f"out-of-pocket จริง และลูกค้าประหยัดเบี้ยได้ {savings:,.0f} บาท/ปี "
            f"เทียบกับแผนไม่มี Deductible ที่ความคุ้มครองระดับเดียวกัน"
        )
    elif covered_amount > 0:
        verdict = "caution"
        headline = f"กรมธรรม์เดิมครอบคลุมได้บางส่วน ({covered_amount:,.0f} จาก {deductible:,.0f} บาท)"
        detail = (
            f"ยังมีส่วนต่างที่ต้องจ่ายเอง {gap_amount:,.0f} บาทต่อครั้งที่เคลม "
            f"หากกรมธรรม์เดิมถูกใช้ไปบางส่วนแล้วในปีนั้น ควรเผื่อสภาพคล่องสำหรับ "
            f"ส่วนต่างนี้ไว้ หรือพิจารณาแผนที่มี Deductible ต่ำกว่านี้ "
            f"เบี้ยที่ประหยัดได้จากการเลือกแผนนี้คือ {savings:,.0f} บาท/ปี"
        )
    else:
        verdict = "not_recommended"
        headline = "กรมธรรม์เดิมไม่สามารถช่วยจ่าย Deductible ได้"
        detail = (
            f"ไม่มีวงเงินเดิมมารองรับ หากเข้ารักษาตัวจะต้องจ่ายเอง "
            f"{deductible:,.0f} บาทแรกทั้งหมด ควรพิจารณาแผนไม่มี Deductible "
            f"หรือแผน Deductible ที่ต่ำกว่านี้ให้เหมาะกับสภาพคล่องของลูกค้า"
        )

    return OffsetResult(
        deductible=deductible,
        old_coverage=old_coverage,
        covered_amount=covered_amount,
        gap_amount=gap_amount,
        fully_covered=fully_covered,
        savings_vs_zero_deductible=savings,
        verdict=verdict,
        headline=headline,
        detail=detail,
    )


VERDICT_BADGE = {
    "recommend": ("mtl-badge-good", "แนะนำ"),
    "caution": ("mtl-badge-warn", "ควรระวัง"),
    "not_recommended": ("mtl-badge-bad", "ไม่แนะนำ"),
}
