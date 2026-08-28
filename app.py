import datetime as dt

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from compare import theme, data, portfolio, live_data
from compare.deductible import analyze_offset, VERDICT_BADGE

st.set_page_config(
    page_title="เปรียบเทียบประกัน | Insurance Compare",
    page_icon="💗",
    layout="wide",
)
st.markdown(f"<style>{theme.CSS}</style>", unsafe_allow_html=True)
portfolio.init_state()

CATEGORIES = ["health", "investment", "life", "retirement"]
CATEGORY_ICON = {"health": "🩺", "investment": "📈", "life": "🛡️", "retirement": "🌅"}


def baht(x, decimals=0):
    try:
        return f"฿{x:,.{decimals}f}"
    except (TypeError, ValueError):
        return "-"


# ---------------------------------------------------------------------------
# sidebar — client profile shared across all tabs
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 👤 โปรไฟล์ลูกค้า")
    age = st.slider("อายุ (ปี)", 18, 80, 35, key="profile_age")
    st.caption(f"ช่วงอายุเบี้ยประกัน: **{data.age_band_label(age)}**")
    sex_label = st.radio("เพศ", ["ชาย", "หญิง"], horizontal=True, key="profile_sex")
    sex = "male" if sex_label == "ชาย" else "female"
    st.caption(
        "เบี้ยต่างกันตามเพศ: ชีวิต/ควบการลงทุนคิดเบี้ยชายสูงกว่า (ความเสี่ยงการเสียชีวิต) "
        "สุขภาพคิดเบี้ยหญิงสูงกว่าเล็กน้อย (การใช้สิทธิ์ที่เกี่ยวกับการคลอดบุตร) "
        "ส่วนบำนาญในตัวอย่างนี้ไม่แยกตามเพศ"
    )
    annual_income = st.number_input(
        "รายได้ต่อปี (บาท) — ใช้คำนวณช่องว่างความคุ้มครอง",
        min_value=0, value=1_200_000, step=100_000, key="profile_income",
    )
    st.divider()
    st.markdown("### 🌐 ข้อมูลสดจากเว็บ")
    st.caption(
        "ดึงข้อมูลแผนสุขภาพล่าสุดจากหน้าเว็บทางการของบริษัทประกัน "
        "(ยังรองรับเฉพาะหมวดสุขภาพ — ดูรายละเอียดในแท็บเปรียบเทียบ)"
    )
    live_status = live_data.cache_status("health")
    if live_status:
        ts = dt.datetime.fromtimestamp(live_status["fetched_at"]).strftime("%d %b %Y %H:%M")
        ok_n = sum(1 for r in live_status["results"] if r["ok"])
        st.caption(f"อัปเดตล่าสุด: {ts} — สำเร็จ {ok_n}/{len(live_status['results'])} บริษัท")
    else:
        st.caption("ยังไม่เคยดึงข้อมูลสด")
    if st.button("🔄 ดึงข้อมูลล่าสุดจากเว็บ (Live Update)", key="live_update_btn"):
        with st.status("กำลังดึงข้อมูลจากเว็บไซต์บริษัทประกัน...", expanded=True) as sb_status:
            def _progress(i, n, name):
                st.write(f"[{i + 1}/{n}] กำลังดึง {name} ...")
            _results = live_data.fetch_category("health", progress_cb=_progress)
            live_data.save_results("health", _results)
            _ok = sum(1 for r in _results if r.ok)
            for r in _results:
                if not r.ok:
                    st.write(f"⚠️ {r.insurer}: ดึงไม่สำเร็จ ({r.error[:80]})")
            sb_status.update(
                label=f"อัปเดตเสร็จสิ้น — สำเร็จ {_ok}/{len(_results)} บริษัท",
                state="complete",
            )
        st.rerun()
    st.divider()
    st.markdown(
        "<span class='mtl-note'>ข้อมูลเบี้ยประกันในแอปนี้เป็น "
        "<b>ข้อมูลตัวอย่างเพื่อการสาธิต</b> ไม่ใช่ใบเสนอราคาจริงจากบริษัทประกัน "
        "โปรดขอใบเสนอราคาอย่างเป็นทางการก่อนตัดสินใจซื้อ</span>",
        unsafe_allow_html=True,
    )

st.markdown(
    """
<div class="mtl-hero">
  <h1>💗 Insurance Compare</h1>
  <p>เปรียบเทียบแผนประกันสุขภาพ / ควบการลงทุน / ชีวิต / บำนาญ จากหลายบริษัท —
  พร้อมเครื่องมือวิเคราะห์ Deductible และพอร์ตประกันของลูกค้า</p>
</div>
""",
    unsafe_allow_html=True,
)

tab_compare, tab_deductible, tab_portfolio = st.tabs(
    ["🔍 เปรียบเทียบแผนประกัน", "🩺 วิเคราะห์ Deductible", "💼 พอร์ตประกันของลูกค้า"]
)

# ---------------------------------------------------------------------------
# TAB 1 — Compare
# ---------------------------------------------------------------------------
with tab_compare:
    cat = st.radio(
        "เลือกประเภทประกัน",
        CATEGORIES,
        format_func=lambda c: f"{CATEGORY_ICON[c]} {theme.CATEGORY_LABELS_TH[c]}",
        horizontal=True,
        key="compare_category",
    )
    st.markdown("<div class='mtl-card'>", unsafe_allow_html=True)

    if cat == "health":
        df = data.health_df(age=age, sex=sex)
        insurers = st.multiselect("บริษัทประกัน", sorted(df["insurer"].unique()), key="h_insurers")
        ded_filter = st.multiselect(
            "Deductible (บาท)", data.DEDUCTIBLE_TIERS,
            default=data.DEDUCTIBLE_TIERS, format_func=lambda v: f"{v:,}", key="h_ded",
        )
        view = df[df["deductible_thb"].isin(ded_filter)]
        if insurers:
            view = view[view["insurer"].isin(insurers)]
        view = view.sort_values("annual_premium")

        st.dataframe(
            view[[
                "insurer", "product_name", "deductible_thb", "annual_premium",
                "ipd_annual_limit", "room_rate_per_day", "opd_limit_per_visit",
                "opd_visits_per_year", "day_surgery_covered",
            ]].rename(columns={
                "insurer": "บริษัท", "product_name": "แผน", "deductible_thb": "Deductible",
                "annual_premium": "เบี้ยต่อปี", "ipd_annual_limit": "วงเงิน IPD/ปี",
                "room_rate_per_day": "ค่าห้อง/วัน", "opd_limit_per_visit": "OPD/ครั้ง",
                "opd_visits_per_year": "OPD ครั้ง/ปี", "day_surgery_covered": "ผ่าตัดเดย์เคส",
            }),
            hide_index=True, use_container_width=True,
            column_config={
                "เบี้ยต่อปี": st.column_config.NumberColumn(format="฿%d"),
                "Deductible": st.column_config.NumberColumn(format="฿%d"),
                "วงเงิน IPD/ปี": st.column_config.NumberColumn(format="฿%d"),
                "ค่าห้อง/วัน": st.column_config.NumberColumn(format="฿%d"),
                "OPD/ครั้ง": st.column_config.NumberColumn(format="฿%d"),
            },
        )

        fig = px.line(
            view.sort_values(["product_name", "deductible_thb"]),
            x="deductible_thb", y="annual_premium", color="product_name",
            markers=True,
            labels={"deductible_thb": "Deductible (บาท)", "annual_premium": "เบี้ยต่อปี (บาท)", "product_name": "แผน"},
            title=f"เบี้ยประกันสุขภาพ ณ อายุ {age} ปี ({sex_label}) ตามระดับ Deductible",
            color_discrete_sequence=px.colors.sequential.RdPu[2:],
        )
        st.plotly_chart(theme.plotly_layout(fig), use_container_width=True)
        st.caption(
            "ยิ่งเลือก Deductible สูง เบี้ยยิ่งถูกลง — ไปที่แท็บ "
            "**🩺 วิเคราะห์ Deductible** เพื่อดูว่ากรมธรรม์เดิมของลูกค้าช่วยจ่าย "
            "ส่วนแรกนี้ได้หรือไม่"
        )

        with st.expander("🌐 ข้อมูลสดจากเว็บไซต์บริษัทประกัน (ทดลอง)"):
            st.markdown(
                "<span class='mtl-note'>⚠️ ข้อมูลชุดนี้ดึงจากหน้าเว็บทางการของแต่ละ"
                "บริษัทโดยอัตโนมัติ (AI ช่วยอ่านหน้าเว็บ) อาจไม่ครบทุกแผน ไม่ครบทุก"
                "ระดับ Deductible และเบี้ยที่เจอมักเป็นตัวอย่างของช่วงอายุเดียว "
                "ไม่ใช่ใบเสนอราคาจริง — ใช้เป็นจุดเริ่มต้นแล้วตรวจสอบกับลิงก์ต้นทาง "
                "หรือขอใบเสนอราคาก่อนใช้กับลูกค้าเสมอ</span>",
                unsafe_allow_html=True,
            )
            live_rows = live_data.live_rows("health")
            if not live_rows:
                st.caption(
                    "ยังไม่มีข้อมูลสด — กดปุ่ม '🔄 ดึงข้อมูลล่าสุดจากเว็บ' ที่แถบด้านซ้าย"
                )
            else:
                ldf = pd.DataFrame(live_rows)
                ldf["fetched_at"] = ldf["fetched_at"].apply(
                    lambda t: dt.datetime.fromtimestamp(t).strftime("%d %b %Y %H:%M")
                )
                st.dataframe(
                    ldf[[
                        "insurer", "product_name", "deductible_thb", "annual_premium",
                        "room_rate_per_day", "ipd_annual_limit", "source_url", "fetched_at",
                    ]].rename(columns={
                        "insurer": "บริษัท", "product_name": "แผน (ตามที่พบบนเว็บ)",
                        "deductible_thb": "Deductible", "annual_premium": "เบี้ยที่พบ (ตัวอย่าง)",
                        "room_rate_per_day": "ค่าห้อง/วัน", "ipd_annual_limit": "วงเงินคุ้มครอง",
                        "source_url": "แหล่งที่มา", "fetched_at": "ดึงเมื่อ",
                    }),
                    hide_index=True, use_container_width=True,
                    column_config={
                        "แหล่งที่มา": st.column_config.LinkColumn(display_text="เปิดหน้าเว็บ"),
                        "เบี้ยที่พบ (ตัวอย่าง)": st.column_config.NumberColumn(format="฿%d"),
                        "ค่าห้อง/วัน": st.column_config.NumberColumn(format="฿%d"),
                        "วงเงินคุ้มครอง": st.column_config.NumberColumn(format="฿%d"),
                        "Deductible": st.column_config.NumberColumn(format="฿%d"),
                    },
                )
                covered_insurers = {r["insurer"] for r in live_rows}
                missing = [i for i in data.INSURERS if i not in covered_insurers]
                if missing:
                    st.caption(
                        "ยังไม่มีแหล่งข้อมูลสาธารณะที่ยืนยันแล้วสำหรับ: " + ", ".join(missing)
                    )

    elif cat == "investment":
        df = data.investment_df(sex=sex)
        insurers = st.multiselect("บริษัทประกัน", sorted(df["insurer"].unique()), key="i_insurers")
        view = df[df["insurer"].isin(insurers)] if insurers else df
        view = view.sort_values("avg_annual_return_5y_pct", ascending=False)

        st.dataframe(
            view.rename(columns={
                "insurer": "บริษัท", "product_name": "แผน",
                "min_annual_premium": "เบี้ยขั้นต่ำ/ปี", "life_coverage_multiple": "ทุนประกัน (เท่าของเบี้ย)",
                "fund_choices_count": "จำนวนกองทุนให้เลือก", "avg_fund_mgmt_fee_pct": "ค่าธรรมเนียมกองทุน (%)",
                "avg_annual_return_5y_pct": "ผลตอบแทนเฉลี่ย 5 ปี (%)", "surrender_charge_years": "ปีที่มีค่าธรรมเนียมเวนคืน",
                "risk_level": "ระดับความเสี่ยง (1-5)",
            }),
            hide_index=True, use_container_width=True,
            column_config={"เบี้ยขั้นต่ำ/ปี": st.column_config.NumberColumn(format="฿%d")},
        )
        fig = px.scatter(
            view, x="avg_fund_mgmt_fee_pct", y="avg_annual_return_5y_pct",
            size="min_annual_premium", color="insurer", text="product_name",
            labels={"avg_fund_mgmt_fee_pct": "ค่าธรรมเนียมกองทุน (%)", "avg_annual_return_5y_pct": "ผลตอบแทนเฉลี่ย 5 ปี (%)"},
            title="ผลตอบแทน vs ค่าธรรมเนียม (ขนาดจุด = เบี้ยขั้นต่ำ)",
            color_discrete_sequence=px.colors.sequential.RdPu[3:],
        )
        fig.update_traces(textposition="top center")
        st.plotly_chart(theme.plotly_layout(fig), use_container_width=True)
        st.caption(
            "⚠️ ผลตอบแทนเป็นข้อมูลตัวอย่างเพื่อการสาธิตเท่านั้น ผลตอบแทนจริงของ "
            "ประกันควบการลงทุนขึ้นอยู่กับกองทุนที่เลือกและไม่รับประกัน"
        )

    elif cat == "life":
        df = data.life_df(age=age, sex=sex)
        life_type = st.multiselect("ประเภท", sorted(df["life_type"].unique()), key="l_type")
        insurers = st.multiselect("บริษัทประกัน", sorted(df["insurer"].unique()), key="l_insurers")
        view = df.copy()
        if life_type:
            view = view[view["life_type"].isin(life_type)]
        if insurers:
            view = view[view["insurer"].isin(insurers)]
        view = view.sort_values("annual_premium")

        st.dataframe(
            view[[
                "insurer", "product_name", "life_type", "sum_assured", "annual_premium",
                "premium_payment_years", "coverage_to_age", "cash_value_pct_at_year20",
            ]].rename(columns={
                "insurer": "บริษัท", "product_name": "แผน", "life_type": "ประเภท",
                "sum_assured": "ทุนประกัน", "annual_premium": "เบี้ยต่อปี",
                "premium_payment_years": "ปีที่ชำระเบี้ย", "coverage_to_age": "คุ้มครองถึงอายุ",
                "cash_value_pct_at_year20": "มูลค่าเวนคืนปีที่ 20 (%เบี้ยสะสม)",
            }),
            hide_index=True, use_container_width=True,
            column_config={
                "ทุนประกัน": st.column_config.NumberColumn(format="฿%d"),
                "เบี้ยต่อปี": st.column_config.NumberColumn(format="฿%d"),
            },
        )
        fig = px.bar(
            view, x="product_name", y="annual_premium", color="life_type",
            labels={"product_name": "แผน", "annual_premium": "เบี้ยต่อปี (บาท)", "life_type": "ประเภท"},
            title=f"เบี้ยประกันชีวิต ณ อายุ {age} ปี ({sex_label}, ทุนประกันอ้างอิงในตาราง)",
            color_discrete_map={"Whole Life": theme.PRIMARY, "Term Life": theme.ACCENT_GOLD},
        )
        fig.update_xaxes(tickangle=-30)
        st.plotly_chart(theme.plotly_layout(fig), use_container_width=True)

    else:  # retirement
        df = data.retirement_df(age=age, sex=sex)
        insurers = st.multiselect("บริษัทประกัน", sorted(df["insurer"].unique()), key="r_insurers")
        view = df[df["insurer"].isin(insurers)] if insurers else df
        view = view.sort_values("estimated_irr_pct", ascending=False)

        st.dataframe(
            view.rename(columns={
                "insurer": "บริษัท", "product_name": "แผน", "sum_assured": "ทุนประกัน",
                "annual_premium": "เบี้ยต่อปี", "premium_payment_years": "ปีที่ชำระเบี้ย",
                "payout_start_age": "เริ่มรับบำนาญอายุ", "payout_end_age": "รับถึงอายุ",
                "guaranteed_annual_payout_pct": "บำนาญ/ปี (% ทุนประกัน)", "estimated_irr_pct": "IRR โดยประมาณ (%)",
            }),
            hide_index=True, use_container_width=True,
            column_config={
                "ทุนประกัน": st.column_config.NumberColumn(format="฿%d"),
                "เบี้ยต่อปี": st.column_config.NumberColumn(format="฿%d"),
            },
        )
        view = view.assign(
            annual_payout=lambda d: d["sum_assured"] * d["guaranteed_annual_payout_pct"] / 100
        )
        fig = px.bar(
            view, x="product_name", y="annual_payout", color="insurer",
            labels={"product_name": "แผน", "annual_payout": "บำนาญที่ได้รับต่อปี (บาท)"},
            title="บำนาญรับต่อปี ณ ทุนประกัน 1,000,000 บาท",
            color_discrete_sequence=px.colors.sequential.RdPu[2:],
        )
        fig.update_xaxes(tickangle=-30)
        st.plotly_chart(theme.plotly_layout(fig), use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# TAB 2 — Deductible analyzer
# ---------------------------------------------------------------------------
with tab_deductible:
    st.markdown(
        "<div class='mtl-card mtl-card-hi'>"
        "<b>แนวคิด:</b> แผนสุขภาพแบบมี Deductible เบี้ยถูกกว่า เพราะลูกค้าต้อง "
        "จ่ายค่ารักษาส่วนแรกเองก่อนแผนใหม่จะเริ่มจ่าย ถ้าลูกค้ามี "
        "<b>กรมธรรม์สุขภาพเดิม</b> (ส่วนตัวหรือประกันกลุ่มบริษัท) ที่ยังมีวงเงิน "
        "เหลือมากพอ กรมธรรม์เดิมจะจ่ายส่วนแรกแทนได้ ทำให้ซื้อแผนใหม่แบบมี "
        "Deductible ในราคาที่ถูกลงได้อย่างปลอดภัย</div>",
        unsafe_allow_html=True,
    )

    hdf_raw = data.health_df(age=age, sex=sex)
    col1, col2 = st.columns(2)
    with col1:
        product_names = hdf_raw[["insurer", "product_name"]].drop_duplicates()
        product_label = product_names["insurer"] + " — " + product_names["product_name"]
        choice = st.selectbox("แผนสุขภาพใหม่ที่สนใจซื้อ", product_label, key="ded_plan")
        row_mask = (hdf_raw["insurer"] + " — " + hdf_raw["product_name"]) == choice
        plan_rows = hdf_raw[row_mask].sort_values("deductible_thb")
    with col2:
        st.metric("อายุ/เพศที่ใช้คำนวณเบี้ย", f"{age} ปี ({data.age_band_label(age)}) — {sex_label}")
        st.metric("วงเงิน IPD ต่อปีของแผนนี้", baht(plan_rows["ipd_annual_limit"].iloc[0]))

    st.dataframe(
        plan_rows[["deductible_thb", "annual_premium", "room_rate_per_day"]].rename(
            columns={"deductible_thb": "Deductible", "annual_premium": "เบี้ยต่อปี", "room_rate_per_day": "ค่าห้อง/วัน"}
        ),
        hide_index=True, use_container_width=True,
        column_config={
            "Deductible": st.column_config.NumberColumn(format="฿%d"),
            "เบี้ยต่อปี": st.column_config.NumberColumn(format="฿%d"),
            "ค่าห้อง/วัน": st.column_config.NumberColumn(format="฿%d"),
        },
    )

    st.markdown("#### กรมธรรม์เดิมของลูกค้า")
    existing_health = [p for p in portfolio.get_policies() if p.get("category") == "health"]
    use_portfolio = False
    old_coverage = 0
    old_source_label = "-"
    if existing_health:
        use_portfolio = st.checkbox(
            "ใช้วงเงินจากกรมธรรม์สุขภาพในพอร์ตของลูกค้า (แท็บ 💼 พอร์ตประกัน)", value=True, key="ded_use_pf"
        )
    if use_portfolio and existing_health:
        pf_choice = st.selectbox(
            "เลือกกรมธรรม์เดิมจากพอร์ต",
            existing_health,
            format_func=lambda p: f"{p['insurer']} — {p['product_name']} (วงเงิน {baht(p.get('coverage_value', 0))})",
            key="ded_pf_pick",
        )
        old_coverage = pf_choice.get("coverage_value", 0)
        old_source_label = f"{pf_choice['insurer']} — {pf_choice['product_name']}"
    else:
        c1, c2 = st.columns(2)
        with c1:
            old_source_label = st.text_input(
                "แหล่งที่มาของวงเงินเดิม", value="ประกันสุขภาพกลุ่มบริษัท", key="ded_manual_src"
            )
        with c2:
            old_coverage = st.number_input(
                "วงเงินคงเหลือที่ใช้จ่ายส่วนแรกได้ (บาท/ปี)", min_value=0, value=100_000, step=10_000,
                key="ded_manual_cov",
            )

    st.markdown("#### ผลการวิเคราะห์แต่ละระดับ Deductible")
    zero_ded_premium = plan_rows.loc[plan_rows["deductible_thb"] == 0, "annual_premium"].iloc[0]
    results = []
    for _, r in plan_rows.iterrows():
        res = analyze_offset(
            deductible=int(r["deductible_thb"]),
            old_coverage=int(old_coverage),
            premium_at_deductible=float(r["annual_premium"]),
            premium_at_zero_deductible=float(zero_ded_premium),
        )
        results.append((r, res))

    best = max(
        (res for _, res in results if res.verdict == "recommend"),
        key=lambda r: r.savings_vs_zero_deductible, default=None,
    )
    if best:
        st.markdown(
            f"<div class='mtl-card mtl-card-hi'><span class='mtl-badge mtl-badge-good'>แนะนำ</span> "
            f"&nbsp; เลือก Deductible <b>{baht(best.deductible)}</b> — {best.headline}<br>"
            f"<span class='mtl-note'>{best.detail}</span></div>",
            unsafe_allow_html=True,
        )

    cols = st.columns(len(results))
    for c, (r, res) in zip(cols, results):
        badge_class, badge_label = VERDICT_BADGE[res.verdict]
        with c:
            st.markdown(
                f"<div class='mtl-card'>"
                f"<span class='mtl-badge {badge_class}'>{badge_label}</span><br><br>"
                f"<b>Deductible {baht(res.deductible)}</b><br>"
                f"เบี้ย {baht(r['annual_premium'])}/ปี<br>"
                f"ประหยัด {baht(res.savings_vs_zero_deductible)}/ปี<br>"
                f"<span class='mtl-note'>ครอบคลุมได้ {baht(res.covered_amount)} "
                f"ส่วนต่าง {baht(res.gap_amount)}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[f"{baht(r['deductible_thb'])}" for r, _ in results],
        y=[r["annual_premium"] for r, _ in results],
        marker_color=theme.PRIMARY, name="เบี้ยต่อปี",
    ))
    fig.add_hline(y=old_coverage, line_dash="dot", line_color=theme.ACCENT_GOLD,
                  annotation_text=f"วงเงินกรมธรรม์เดิม: {baht(old_coverage)}")
    fig.update_layout(title="เบี้ยประกันแต่ละระดับ Deductible เทียบวงเงินกรมธรรม์เดิม",
                       xaxis_title="Deductible", yaxis_title="บาท")
    st.plotly_chart(theme.plotly_layout(fig), use_container_width=True)

    st.markdown("#### เพิ่มแผนนี้เข้าพอร์ต (จำลอง)")
    target_ded = st.selectbox(
        "เลือกระดับ Deductible ที่จะซื้อ", plan_rows["deductible_thb"].tolist(),
        format_func=lambda v: baht(v), key="ded_add_choice",
    )
    if st.button("➕ เพิ่มเข้าพอร์ต (จำลอง)", key="ded_add_btn"):
        r = plan_rows[plan_rows["deductible_thb"] == target_ded].iloc[0]
        portfolio.add_policy(dict(
            category="health", insurer=r["insurer"], product_name=r["product_name"],
            annual_premium=float(r["annual_premium"]), coverage_value=float(r["ipd_annual_limit"]),
            deductible_thb=int(r["deductible_thb"]), kind="simulated",
        ))
        st.success("เพิ่มแผนนี้เข้าพอร์ต (จำลอง) แล้ว — ดูผลกระทบในแท็บ 💼 พอร์ตประกัน")

# ---------------------------------------------------------------------------
# TAB 3 — Portfolio
# ---------------------------------------------------------------------------
with tab_portfolio:
    st.markdown("#### ➕ เพิ่มกรมธรรม์ที่ลูกค้ามีอยู่ในปัจจุบัน")
    with st.form("add_existing_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            f_cat = st.selectbox(
                "ประเภทประกัน", CATEGORIES,
                format_func=lambda c: f"{CATEGORY_ICON[c]} {theme.CATEGORY_LABELS_TH[c]}", key="f_cat",
            )
            f_insurer = st.selectbox("บริษัทประกัน", data.INSURERS + ["อื่นๆ"], key="f_insurer")
        with c2:
            f_name = st.text_input("ชื่อแผน / กรมธรรม์", key="f_name")
            f_premium = st.number_input("เบี้ยต่อปี (บาท)", min_value=0, value=30_000, step=1_000, key="f_premium")
        with c3:
            cov_label = {
                "health": "วงเงิน IPD ต่อปี (บาท)", "investment": "ทุนประกันชีวิต (บาท)",
                "life": "ทุนประกัน (บาท)", "retirement": "เงินบำนาญรับต่อปี (บาท)",
            }[f_cat]
            f_coverage = st.number_input(cov_label, min_value=0, value=500_000, step=50_000, key="f_coverage")
            f_deductible = 0
            if f_cat == "health":
                f_deductible = st.selectbox(
                    "Deductible เดิม (บาท)", data.DEDUCTIBLE_TIERS,
                    format_func=lambda v: baht(v), key="f_deductible",
                )
        submitted = st.form_submit_button("เพิ่มกรมธรรม์นี้")
        if submitted and f_name.strip():
            payload = dict(
                category=f_cat, insurer=f_insurer, product_name=f_name.strip(),
                annual_premium=float(f_premium), coverage_value=float(f_coverage), kind="existing",
            )
            if f_cat == "health":
                payload["deductible_thb"] = int(f_deductible)
            if f_cat == "retirement":
                payload["annual_payout"] = float(f_coverage)
            portfolio.add_policy(payload)
            st.success(f"เพิ่ม {f_name} แล้ว")

    all_policies = portfolio.get_policies()
    existing_policies = [p for p in all_policies if p["kind"] == "existing"]
    simulated_policies = [p for p in all_policies if p["kind"] == "simulated"]

    def render_policy_table(policies, title):
        st.markdown(f"##### {title}")
        if not policies:
            st.caption("ยังไม่มีรายการ")
            return
        for p in policies:
            cols = st.columns([2, 3, 2, 2, 2, 1])
            cols[0].write(f"{CATEGORY_ICON.get(p['category'], '')} {theme.CATEGORY_LABELS_TH.get(p['category'], p['category'])}")
            cols[1].write(f"**{p['insurer']}**\n\n{p['product_name']}")
            cols[2].write(baht(p.get("annual_premium", 0)))
            cols[3].write(baht(p.get("coverage_value", 0)))
            ded = p.get("deductible_thb")
            cols[4].write(baht(ded) if ded is not None else "-")
            if cols[5].button("🗑️", key=f"rm_{p['id']}"):
                portfolio.remove_policy(p["id"])
                st.rerun()

    st.divider()
    render_policy_table(existing_policies, "📋 กรมธรรม์ที่มีอยู่ในปัจจุบัน")
    if simulated_policies:
        st.markdown(
            "<span class='mtl-badge mtl-badge-gold'>จำลอง</span> "
            "<span class='mtl-note'>รายการด้านล่างคือแผนใหม่ที่ยังไม่ได้ซื้อ ใช้ดูผลกระทบก่อนตัดสินใจ</span>",
            unsafe_allow_html=True,
        )
        render_policy_table(simulated_policies, "🧪 แผนใหม่ที่กำลังพิจารณา (จำลอง)")
        if st.button("ล้างรายการจำลองทั้งหมด", key="clear_sim_btn"):
            portfolio.clear_simulated()
            st.rerun()

    st.divider()
    st.markdown("#### 📊 สรุปพอร์ตประกัน")
    view_mode = st.radio(
        "มุมมอง", ["เฉพาะกรมธรรม์ปัจจุบัน", "รวมแผนที่จำลองไว้ด้วย"],
        horizontal=True, key="pf_view_mode",
        disabled=not simulated_policies,
    )
    active_policies = all_policies if (view_mode == "รวมแผนที่จำลองไว้ด้วย" and simulated_policies) else existing_policies
    summary = portfolio.summarize(active_policies, annual_income=annual_income)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("เบี้ยรวมต่อปี", baht(summary["total_premium"]))
    m2.metric("วงเงินสุขภาพรวม (IPD)", baht(summary["health_coverage"]),
              delta=f"-{baht(summary['health_gap'])} ต่ำกว่าเกณฑ์" if summary["health_gap"] > 0 else "ครบเกณฑ์แล้ว",
              delta_color="inverse" if summary["health_gap"] > 0 else "normal")
    m3.metric("ทุนชีวิตรวม", baht(summary["life_coverage"]),
              delta=f"-{baht(summary['life_gap'])} ต่ำกว่าเป้า 10 เท่ารายได้" if summary["life_gap"] > 0 else "ครบเป้าหมายแล้ว",
              delta_color="inverse" if summary["life_gap"] > 0 else "normal")
    m4.metric("บำนาญรับต่อปี", baht(summary["retirement_annual_payout"]),
              delta=f"-{baht(summary['retirement_gap'])} ต่ำกว่าเป้า 70% รายได้" if summary["retirement_gap"] > 0 else "ครบเป้าหมายแล้ว",
              delta_color="inverse" if summary["retirement_gap"] > 0 else "normal")

    cA, cB = st.columns(2)
    with cA:
        if summary["by_category"]:
            cat_df = pd.DataFrame([
                {"ประเภท": theme.CATEGORY_LABELS_TH[k], "เบี้ยต่อปี": v["premium"], "cat": k}
                for k, v in summary["by_category"].items()
            ])
            fig = px.pie(
                cat_df, names="ประเภท", values="เบี้ยต่อปี", hole=0.55,
                color="cat", color_discrete_map={k: theme.CATEGORY_COLORS[k] for k in CATEGORIES},
                title="สัดส่วนเบี้ยประกันตามประเภท",
            )
            st.plotly_chart(theme.plotly_layout(fig, height=340), use_container_width=True)
        else:
            st.caption("เพิ่มกรมธรรม์เพื่อดูสัดส่วนเบี้ยประกัน")
    with cB:
        gap_df = pd.DataFrame([
            {"เป้าหมาย": "สุขภาพ (เทียบเกณฑ์ 3M)", "มี": summary["health_coverage"], "ขาด": summary["health_gap"]},
            {"เป้าหมาย": "ชีวิต (เทียบ 10x รายได้)", "มี": summary["life_coverage"], "ขาด": summary["life_gap"]},
            {"เป้าหมาย": "บำนาญ/ปี (เทียบ 70% รายได้)", "มี": summary["retirement_annual_payout"], "ขาด": summary["retirement_gap"]},
        ])
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(name="มีอยู่แล้ว", x=gap_df["เป้าหมาย"], y=gap_df["มี"], marker_color=theme.PRIMARY))
        fig2.add_trace(go.Bar(name="ยังขาด", x=gap_df["เป้าหมาย"], y=gap_df["ขาด"], marker_color=theme.BORDER))
        fig2.update_layout(barmode="stack", title="ความคุ้มครองที่มี vs ช่องว่างเทียบเกณฑ์")
        st.plotly_chart(theme.plotly_layout(fig2, height=340), use_container_width=True)

    st.divider()
    st.markdown("#### 🧪 จำลองการซื้อแผนใหม่เพิ่ม")
    sim_cat = st.selectbox(
        "ประเภทประกันที่จะเพิ่ม", CATEGORIES,
        format_func=lambda c: f"{CATEGORY_ICON[c]} {theme.CATEGORY_LABELS_TH[c]}", key="sim_cat",
    )
    if sim_cat == "health":
        sdf = data.health_df(age=age, sex=sex)
    elif sim_cat == "investment":
        sdf = data.investment_df(sex=sex)
    elif sim_cat == "life":
        sdf = data.life_df(age=age, sex=sex)
    else:
        sdf = data.retirement_df(age=age, sex=sex)
        sdf = sdf.assign(annual_payout=lambda d: d["sum_assured"] * d["guaranteed_annual_payout_pct"] / 100)

    label_series = sdf["insurer"] + " — " + sdf["product_name"] + (
        sdf["deductible_thb"].map(lambda v: f" (Ded {v:,.0f})") if sim_cat == "health" else ""
    )
    sim_choice = st.selectbox("เลือกแผน", label_series, key="sim_choice")
    sim_row = sdf[label_series == sim_choice].iloc[0]

    premium_col = "annual_premium" if "annual_premium" in sdf.columns else "min_annual_premium"
    if sim_cat == "investment":
        coverage_val = sim_row["min_annual_premium"] * sim_row["life_coverage_multiple"]
    elif sim_cat == "health":
        coverage_val = sim_row["ipd_annual_limit"]
    elif sim_cat == "life":
        coverage_val = sim_row["sum_assured"]
    else:
        coverage_val = sim_row["sum_assured"]

    proj_premium = summary["total_premium"] + float(sim_row[premium_col])
    st.markdown(
        f"<div class='mtl-card'>เบี้ยเพิ่ม <b>{baht(sim_row[premium_col])}</b>/ปี &nbsp;→&nbsp; "
        f"เบี้ยรวมพอร์ตจะเป็น <b>{baht(proj_premium)}</b>/ปี</div>",
        unsafe_allow_html=True,
    )
    if st.button("➕ เพิ่มแผนนี้เป็นรายการจำลอง", key="sim_add_btn"):
        payload = dict(
            category=sim_cat, insurer=sim_row["insurer"], product_name=sim_row["product_name"],
            annual_premium=float(sim_row[premium_col]), coverage_value=float(coverage_val), kind="simulated",
        )
        if sim_cat == "health":
            payload["deductible_thb"] = int(sim_row["deductible_thb"])
        if sim_cat == "retirement":
            payload["annual_payout"] = float(sim_row.get("annual_payout", 0))
        portfolio.add_policy(payload)
        st.success("เพิ่มเป็นรายการจำลองแล้ว — สลับมุมมองด้านบนเป็น 'รวมแผนที่จำลองไว้ด้วย' เพื่อดูผลกระทบ")
        st.rerun()
