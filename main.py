import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import zoneinfo

# ==========================================
# 1. 페이지 기본 설정 및 스타일 지정
# ==========================================
st.set_page_config(
    page_title="어제 박스오피스 순위",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 어제의 박스오피스 TOP 10")

# ==========================================
# 2. 한국 시간(KST) 기준 '어제' 날짜 계산
# ==========================================
# 배포 서버(Streamlit Cloud)의 시계가 UTC(세계 표준시)일 수 있으므로 
# 명시적으로 'Asia/Seoul' 타임존을 지정하여 한국 시간 기준 어제 날짜를 구합니다.
try:
    kst = zoneinfo.ZoneInfo("Asia/Seoul")
    now_kst = datetime.now(kst)
except Exception:
    # 혹시 타임존 모듈 문제 발생 시 기본 UTC+9시간을 수동 계산합니다.
    now_kst = datetime.utcnow() + timedelta(hours=9)

yesterday = now_kst - timedelta(days=1)
target_dt = yesterday.strftime("%Y%m%d")      # API 요청용 날짜 format (YYYYMMDD)
display_date = yesterday.strftime("%Y년 %m월 %d일") # 화면 표시용 format

st.caption(f"📅 기준일자: **{display_date}** (한국 시간 기준)")

# ==========================================
# 3. Streamlit Secrets에서 API 키 가져오기
# ==========================================
# st.secrets를 활용하여 KOBIS_KEY를 안전하게 불러옵니다.
if "KOBIS_KEY" not in st.secrets or not st.secrets["KOBIS_KEY"]:
    st.error("🚨 **API 키 설정 필요**")
    st.info(
        "Streamlit Cloud 대시보드의 **Settings > Secrets**에서 아래와 같이 인증키를 등록해 주세요.\n\n"
        "```toml\n"
        'KOBIS_KEY = "발급받은_KOBIS_API_KEY"\n'
        "```\n"
        "자세한 사항은 [KOBIS Open API 사이트](https://www.kobis.or.kr/kobisopenapi/)를 참고하세요."
    )
    st.stop()  # 키가 없으면 아래 로직을 실행하지 않고 멈춥니다.

api_key = st.secrets["KOBIS_KEY"]

# ==========================================
# 4. KOBIS API 데이터 호출
# ==========================================
url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
params = {
    "key": api_key,
    "targetDt": target_dt
}

try:
    response = requests.get(url, params=params, timeout=10)
    
    # HTTP 상태 코드가 200이 아닌 경우 예외 처리
    if response.status_code != 200:
        st.error("🚨 **서버 통신 오류**")
        st.warning("KOBIS API 서버와의 통신에 실패했습니다. 잠시 후 다시 시도해 주세요.")
        st.stop()
        
    data = response.json()

except Exception as e:
    st.error("🚨 **네트워크 요청 실패**")
    st.warning("인터넷 연결을 확인하거나 KOBIS 서비스 상태를 점검해 주세요.")
    st.stop()

# ==========================================
# 5. API 응답 데이터 검증 및 에러 안내
# ==========================================
# 1) 잘못된 키 사용 등으로 faultInfo 응답이 오는 경우
if "faultInfo" in data:
    st.error("🚨 **KOBIS API 인증 오류 (faultInfo 발생)**")
    st.info(
        "💡 **확인해 보세요:**\n"
        "1. Secrets에 입력한 `KOBIS_KEY` 값이 정확한지 확인해 주세요.\n"
        "2. KOBIS 공식 홈페이지에서 API 키의 활용 신청이 완료되었는지 확인해 주세요.\n\n"
        f"**오류 메시지:** `{data['faultInfo'].get('message', '알 수 없는 오류')}`"
    )
    st.stop()

# 2) boxOfficeResult 응답 객체가 없는 경우
if "boxOfficeResult" not in data:
    st.error("🚨 **올바르지 않은 응답 형식**")
    st.warning("KOBIS API 응답 형식이 예상과 다릅니다. 관리자에게 문의해 주세요.")
    st.stop()

box_office_result = data["boxOfficeResult"]
daily_list = box_office_result.get("dailyBoxOfficeList", [])

# 3) 영화 목록 데이터가 비어 있는 경우
if not daily_list:
    st.warning("⚠️ **조회된 영화 목록이 없습니다.**")
    st.info(
        "💡 **확인해 보세요:**\n"
        "1. KOBIS 집계 시점에 따라 어제 자 데이터 집계가 지연될 수 있습니다.\n"
        "2. 날짜 파라미터가 올바른 형식(YYYYMMDD)으로 입력되었는지 확인해 주세요."
    )
    st.stop()

# ==========================================
# 6. 데이터 전처리 (문자열 -> 숫자 변환 등)
# ==========================================
df = pd.DataFrame(daily_list)

# API 응답 결과는 모두 문자열로 오므로 숫자형으로 변환합니다.
df["rank"] = pd.to_numeric(df["rank"])            # 순위
df["audiCnt"] = pd.to_numeric(df["audiCnt"])      # 일일 관객수
df["audiAcc"] = pd.to_numeric(df["audiAcc"])      # 누적 관객수
df["scrnCnt"] = pd.to_numeric(df["scrnCnt"])      # 스크린수

# ==========================================
# 7. 1위 영화 지표 카드 (Metrics)
# ==========================================
top_1 = df.iloc[0]

st.subheader(f"🥇 1위 영화: {top_1['movieNm']}")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(
        label="일일 관객수",
        value=f"{top_1['audiCnt']:,} 명"
    )
with col2:
    st.metric(
        label="누적 관객수",
        value=f"{top_1['audiAcc']:,} 명"
    )
with col3:
    st.metric(
        label="스크린 수",
        value=f"{top_1['scrnCnt']:,} 개"
    )

st.divider()

# ==========================================
# 8. 관객수 상위 5편 막대그래프
# ==========================================
st.subheader("📊 관객수 상위 5개 영화")

# 상위 5개 영화 데이터 추출
top_5_df = df.head(5).copy()

# 시각화를 위해 순위 내림차순(그래프 상단에 1위가 오도록) 정리
top_5_chart = top_5_df.iloc[::-1]

# Streamlit 내장 막대그래프 출력
st.bar_chart(
    data=top_5_chart,
    x="movieNm",
    y="audiCnt",
    horizontal=True,
    use_container_width=True
)

st.divider()

# ==========================================
# 9. 박스오피스 전체 순위 표 출력
# ==========================================
st.subheader("📋 박스오피스 전체 순위 표")

# 표에 보여줄 컬럼 선택 및 이름 변경
display_df = df[[
    "rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"
]].copy()

display_df.columns = [
    "순위", "영화명", "개봉일", "일일 관객수", "누적 관객수", "스크린 수"
]

# 관객수/스크린수 수치 천 단위 쉼표(,) 포맷팅
st.dataframe(
    display_df,
    hide_index=True,
    column_config={
        "순위": st.column_config.NumberColumn("순위", format="%d"),
        "일일 관객수": st.column_config.NumberColumn("일일 관객수", format="%d 명"),
        "누적 관객수": st.column_config.NumberColumn("누적 관객수", format="%d 명"),
        "스크린 수": st.column_config.NumberColumn("스크린 수", format="%d 개"),
    },
    use_container_width=True
)
