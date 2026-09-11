"""기업 재무 대시보드: API 연결 전 레이아웃 프로토타입."""
from datetime import date

import plotly.graph_objects as go
import streamlit as st
from data_sources import DataSourceError, fetch_dart_companies, fetch_sec_companies, search_companies
from financials import BALANCE, CASH, INCOME, load_financials
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

COLORS = ["#3182F6", "#F59E42", "#20B89A", "#9A75DB", "#8294B0", "#234F81"]


def secret(name):
    try:
        return str(st.secrets.get(name, "")).strip()
    except (FileNotFoundError, KeyError):
        return ""


@st.cache_data(ttl=86_400, show_spinner=False)
def company_catalog(dart_api_key, sec_user_agent):
    companies, errors = [], []
    for loader, credential in (
        (fetch_dart_companies, dart_api_key),
        (fetch_sec_companies, sec_user_agent),
    ):
        try:
            companies.extend(loader(credential))
        except DataSourceError as error:
            errors.append(str(error))
    return companies, errors


@st.cache_data(ttl=3_600, show_spinner=False, max_entries=32)
def financial_result(company, start_year, start_quarter, end_year, end_quarter,
                     quarterly, dart_api_key, sec_user_agent):
    frame, unit = load_financials(
        company, start_year, end_year, quarterly, dart_api_key, sec_user_agent
    )
    if quarterly:
        allowed = {
            f"{year} Q{quarter}"
            for year in range(start_year, end_year + 1)
            for quarter in range(1, 5)
            if (start_year, start_quarter) <= (year, quarter) <= (end_year, end_quarter)
        }
        frame = frame.loc[[label for label in frame.index if label in allowed]]
    if frame.empty:
        raise DataSourceError("선택한 기간에 표시할 재무정보가 없습니다.")
    return frame, unit


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
st.info("한국 기업은 DART, 미국 기업은 SEC EDGAR의 공식 공시 데이터를 사용합니다.")
dart_api_key = secret("DART_API_KEY")
sec_user_agent = secret("SEC_USER_AGENT")
catalog, catalog_errors = company_catalog(dart_api_key, sec_user_agent)
if not catalog:
    st.error("API 설정을 확인해 주세요. 기업 목록을 불러오지 못했습니다.")
    st.stop()
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
    matches = search_companies(catalog, normalized)
    company = None
    if matches:
        company = st.selectbox("검색 결과", matches, format_func=lambda item: item.label)
        st.caption(f"데이터 출처: {company.source}")
    actions = st.columns([1, 1, 1])
    with actions[0]:
        search_clicked = st.button("기업 검색", type="primary", width="stretch")
    download_slot = actions[1].empty()
    download_slot.download_button("결과 이미지로 저장", data=b"", file_name="financial-report.png",
                                  mime="image/png", disabled=True, width="stretch",
                                  help="조회 결과를 표시한 뒤 저장할 수 있습니다.", key="empty_download")

search_message = None
if search_clicked:
    if (start_year, start_quarter) > (end_year, end_quarter):
        search_message = "시작 기간을 종료 기간 이전으로 설정해 주세요. 기존 조회 결과는 유지됩니다."
    elif not normalized:
        search_message = "기업명 또는 종목코드를 입력해 주세요. 기존 조회 결과는 유지됩니다."
    elif not company:
        search_message = "일치하는 기업을 찾지 못했습니다. 기존 조회 결과는 유지됩니다."
    else:
        try:
            with st.spinner("공시 데이터를 불러오는 중입니다."):
                frame, unit = financial_result(
                    company, start_year, start_quarter, end_year, end_quarter,
                    quarterly, dart_api_key, sec_user_agent,
                )
            st.session_state["result"] = {
                "company": company, "quarterly": quarterly, "frame": frame, "unit": unit,
            }
        except DataSourceError as error:
            search_message = f"{error} 기존 조회 결과는 유지됩니다."

if search_message:
    st.warning(search_message)

if "result" not in st.session_state:
    st.stop()

result = st.session_state["result"]
company, quarterly, frame, unit = (
    result["company"], result["quarterly"], result["frame"], result["unit"]
)
@st.cache_data(show_spinner=False, max_entries=8)
def result_png(frame, name, frequency, unit):
    return render_report(frame, name, frequency, unit,
                         [("01 재무상태", BALANCE), ("02 손익", INCOME), ("03 현금흐름", CASH)], COLORS)

name = company.name
try:
    png = result_png(frame, name, "분기별" if quarterly else "연도별", unit)
    download_slot.download_button("결과 이미지로 저장", data=png,
                                  file_name=f"{name}_{frame.index[0]}_{frame.index[-1]}_재무요약.png",
                                  mime="image/png", width="stretch", on_click="ignore",
                                  help="현재 표시된 조회 결과의 모든 항목을 PNG로 저장합니다.", key="result_download")
except (OSError, ValueError) as error:
    st.warning("이미지를 생성하지 못했습니다. 페이지를 새로고침한 뒤 다시 시도해 주세요.")
    import logging
    logging.getLogger(__name__).exception("Report image generation failed")
st.subheader(f"{company.name} · {company.symbol}")
st.caption(f"{'분기별' if quarterly else '연도별'} · {frame.index[0]} ~ {frame.index[-1]} · {unit} · {company.source}")
chart_section("01 재무상태", "각 보고기간 말의 잔액을 비교합니다.", BALANCE, frame, unit)
chart_section("02 손익", "분기별 조회는 해당 분기 단독 실적, 연도별 조회는 연간 실적을 표시합니다.", INCOME, frame, unit)
chart_section("03 현금흐름", "기간 중 현금 흐름과 기초·기말 잔액을 비교합니다. 범례를 누르면 항목을 숨길 수 있습니다.", CASH, frame, unit)
st.caption("현금 증가(감소)와 세 활동의 합계는 환율변동 효과 등으로 다를 수 있습니다. 실제 데이터 연결 시 조정 항목을 보존합니다.")
with st.expander("3-1 CAPEX · 다음 단계"):
    st.write("기본 화면 확정 후 취득 지출과 계산 기준을 연결합니다. 비율 및 파생 지표도 이후 추가합니다.")
