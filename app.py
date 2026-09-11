"""기업 재무 대시보드: API 연결 전 레이아웃 프로토타입."""
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from report_image import render_report

st.set_page_config(page_title="기업 재무 대시보드", page_icon="📊", layout="wide")
st.markdown("""
<style>
[data-testid="stMainBlockContainer"] {max-width:1180px; margin:auto; padding-top:3rem;}
h1 {letter-spacing:-1.3px;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:16px;}
.intro {color:#6B7684; margin-bottom:26px; font-size:17px;}
</style>
""", unsafe_allow_html=True)

BALANCE = ["자산", "부채", "자본"]
INCOME = ["매출액", "영업이익", "당기순이익"]
CASH = ["영업현금흐름", "투자현금흐름", "재무현금흐름", "현금 및 현금성자산 증가(감소)",
        "기초 현금 및 현금성자산", "기말 현금 및 현금성자산"]
COLORS = ["#3182F6", "#F59E42", "#20B89A", "#9A75DB", "#8294B0", "#234F81"]
# 화면 검토용 검색 목록. 실서비스에서는 DART/SEC 기업 마스터로 교체한다.
COMPANIES = [
    ("삼성전자", "005930", "한국", "DART", "samsung 삼성전자"),
    ("SK하이닉스", "000660", "한국", "DART", "sk hynix 하이닉스"),
    ("Apple", "AAPL", "미국", "SEC EDGAR", "apple 애플"),
    ("Microsoft", "MSFT", "미국", "SEC EDGAR", "microsoft 마이크로소프트"),
]


def demo_data(periods, quarterly):
    """기업 실제 수치와 무관한 가상 데이터. 잔액과 기간 흐름을 구분한다."""
    rows = []
    for year, quarter, label in periods:
        n = (year - 2015) * 4 + (quarter or 4)
        factor = 1 if quarterly else 4
        assets = 1000 + n * 30
        debt = assets * .36
        opening = 100 + (n - (1 if quarterly else 4)) * 3
        operating, investing, financing = 30 * factor, -21 * factor, -6 * factor
        increase = operating + investing + financing
        rows.append([label, assets, debt, assets - debt,
                     (130 + n * 2) * factor, (20 + n * .3) * factor,
                     (14 + n * .2) * factor, operating, investing, financing,
                     increase, opening, opening + increase])
    return pd.DataFrame(rows, columns=["기간"] + BALANCE + INCOME + CASH).set_index("기간")


def chart_section(title, description, columns, frame, unit):
    with st.container(border=True):
        st.subheader(title)
        st.caption(description)
        fig = go.Figure()
        for name, color in zip(columns, COLORS):
            fig.add_bar(x=frame.index.tolist(), y=frame[name].tolist(), name=name,
                        marker_color=color,
                        hovertemplate="%{x}<br>%{y:,.1f} " + unit + "<extra>%{fullData.name}</extra>")
        fig.update_layout(barmode="group", height=370, margin=dict(l=0, r=0, t=20, b=0),
                          legend=dict(orientation="h", y=1.18, x=0),
                          yaxis_title=unit, xaxis=dict(type="category"),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        fig.update_yaxes(zeroline=True, zerolinecolor="#8294B0", gridcolor="#EEF1F4")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        with st.expander("상세 수치 보기"):
            st.dataframe(frame[columns].T, width="stretch")


st.title("기업 재무 대시보드")
st.markdown('<div class="intro">기업의 자산, 실적, 현금 흐름을 기간별로 비교합니다.</div>', unsafe_allow_html=True)
st.info("레이아웃 미리보기 · API 미연결 · 그래프의 모든 수치는 가상 데이터입니다.")
with st.container(border=True):
    query = st.text_input("기업명 또는 종목코드", placeholder="예: 삼성전자, 005930, Apple, AAPL")
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        frequency = st.radio("조회 기준", ["연도별", "분기별"], horizontal=True)
    quarterly = frequency == "분기별"
    with c2:
        start_year = int(st.number_input("시작 연도", 2015, date.today().year, date.today().year - 3))
        start_quarter = st.selectbox("시작 분기", [1, 2, 3, 4], format_func=lambda x: f"{x}분기") if quarterly else 1
    with c3:
        end_year = int(st.number_input("종료 연도", 2015, date.today().year, date.today().year - 1))
        end_quarter = st.selectbox("종료 분기", [1, 2, 3, 4], index=3, format_func=lambda x: f"{x}분기") if quarterly else 4
    st.caption("기간은 회계연도 기준입니다. 실제 조회에서는 기업의 결산월과 보고기간을 함께 표시합니다.")
    normalized = query.strip().casefold()
    matches = [c for c in COMPANIES if normalized and normalized in " ".join((c[0], c[1], c[4])).casefold()]
    company = None
    if matches:
        company = st.selectbox("검색 결과", matches, format_func=lambda c: f"{c[0]} · {c[1]} · {c[2]}")
        st.caption(f"연결 예정 데이터 출처: {company[3]}")
    elif normalized:
        st.warning("미리보기 검색은 삼성전자, SK하이닉스, Apple, Microsoft를 지원합니다.")
    actions = st.columns([1, 1, 1])
    with actions[0]:
        preview = st.button("가상 데이터로 레이아웃 보기", type="primary", width="stretch")
    download_slot = actions[1].empty()
    download_slot.download_button("결과 이미지로 저장", data=b"", file_name="financial-report.png",
                                  mime="image/png", disabled=True, width="stretch",
                                  help="조회 결과를 표시한 뒤 저장할 수 있습니다.", key="empty_download")

if preview:
    if (start_year, start_quarter) > (end_year, end_quarter):
        st.error("시작 기간을 종료 기간 이전으로 설정해 주세요.")
        st.stop()
    if normalized and not company:
        st.error("미리보기 검색 결과가 있는 기업을 입력하거나 기업명을 비워 주세요.")
        st.stop()
    st.session_state["selection"] = (company, quarterly, start_year, start_quarter, end_year, end_quarter)

if "selection" not in st.session_state:
    st.caption("기업명을 비워 두어도 가상 데이터로 화면 구성을 확인할 수 있습니다.")
    for title, names in [("01 재무상태", BALANCE), ("02 손익", INCOME), ("03 현금흐름", CASH)]:
        with st.container(border=True):
            st.subheader(title)
            st.write(" · ".join(names))
    st.stop()

company, quarterly, sy, sq, ey, eq = st.session_state["selection"]
periods = [(y, q, f"{y} Q{q}") for y in range(sy, ey + 1) for q in range(1, 5)
           if (sy, sq) <= (y, q) <= (ey, eq)] if quarterly else [(y, None, str(y)) for y in range(sy, ey + 1)]
frame = demo_data(periods, quarterly)
unit = "백만 USD" if company and company[2] == "미국" else "억 원"
@st.cache_data(show_spinner=False, max_entries=8)
def result_png(frame, name, frequency, unit):
    return render_report(frame, name, frequency, unit,
                         [("01 재무상태", BALANCE), ("02 손익", INCOME), ("03 현금흐름", CASH)], COLORS)

name = company[0] if company else "가상 기업"
try:
    png = result_png(frame, name, "분기별" if quarterly else "연도별", unit)
    download_slot.download_button("결과 이미지로 저장", data=png,
                                  file_name=f"{name}_{periods[0][2]}_{periods[-1][2]}_재무요약.png",
                                  mime="image/png", width="stretch", on_click="ignore",
                                  help="현재 표시된 조회 결과의 모든 항목을 PNG로 저장합니다.", key="result_download")
except (OSError, ValueError) as error:
    st.warning("이미지를 생성하지 못했습니다. 페이지를 새로고침한 뒤 다시 시도해 주세요.")
    import logging
    logging.getLogger(__name__).exception("Report image generation failed")
st.subheader(f"{company[0] if company else '가상 기업'} · 레이아웃 예시")
st.caption(f"적용된 조회 조건: {'분기별' if quarterly else '연도별'} · {periods[0][2]} ~ {periods[-1][2]} · {unit} · 실제 재무정보 아님")
chart_section("01 재무상태", "각 보고기간 말의 잔액을 비교합니다.", BALANCE, frame, unit)
chart_section("02 손익", "분기별 조회는 해당 분기 단독 실적, 연도별 조회는 연간 실적을 표시합니다.", INCOME, frame, unit)
chart_section("03 현금흐름", "기간 중 현금 흐름과 기초·기말 잔액을 비교합니다. 범례를 누르면 항목을 숨길 수 있습니다.", CASH, frame, unit)
st.caption("현금 증가(감소)와 세 활동의 합계는 환율변동 효과 등으로 다를 수 있습니다. 실제 데이터 연결 시 조정 항목을 보존합니다.")
with st.expander("3-1 CAPEX · 다음 단계"):
    st.write("기본 화면 확정 후 취득 지출과 계산 기준을 연결합니다. 비율 및 파생 지표도 이후 추가합니다.")
