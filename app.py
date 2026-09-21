import datetime
import io
import zipfile
import os
import pandas as pd
import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="마켓지니 판매 관리 프로그램",
    page_icon="📦",
    layout="wide",
)

DB_FILE = "market_history.csv"

def load_history():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            if "날짜" in df.columns:
                return df
        except:
            pass
    return pd.DataFrame(columns=[
        "날짜", "판매처", "상품명", "수량", "매출액", "원가", "배송비", "수수료", "순이익"
    ])

def save_history(new_row_df):
    df = load_history()
    df = pd.concat([df, new_row_df], ignore_index=True)
    df.to_csv(DB_FILE, index=False)

st.title("📦 마켓지니 판매 관리 프로그램")
st.markdown(
    "**1단계:** 쿠팡, 스마트스토어, 올웨이즈 등 플랫폼별 발주서를 업로드하여 **키스틱, 냉동식품, 가람식품** 세 군데 공급처별 양식으로 분할 다운로드<br>"
    "**2단계:** **판매 플랫폼별(쿠팡, 스마트스토어, 올웨이즈 등)**로 구분된 상세 매출 및 순이익 분석 대시보드 확인",
    unsafe_allow_html=True,
)
st.markdown("---")

tab1, tab2 = st.tabs(
    ["📥 1단계: 발주서 업로드 및 3개 공급처별 분할", "📈 2단계: 플랫폼별 종합 매출 분석 대시보드"]
)

# -------------------------------------------------------------------------
# 1탭: 플랫폼별 발주서 업로드 -> 세 군데 공급처별 분할 다운로드
# -------------------------------------------------------------------------
with tab1:
    st.header("📥 발주서 업로드 및 3개 공급처별 분할 다운로드")
    st.markdown(
        "어떤 플랫폼(쿠팡, 스마트스토어, 올웨이즈 등)에서 받은 발주서인지 선택하고 업로드해 주세요. "
        "데이터를 분석하여 **키스틱, 냉동식품, 가람식품** 세 군데 공급처별 발주 파일로 나누어 드립니다."
    )

    # 판매 플랫폼 선택
    platform_choice = st.selectbox(
        "🏷️ 업로드할 발주서의 판매 플랫폼 선택",
        ["올웨이즈", "쿠팡", "네이버 스마트스토어", "카카오/기타 플랫폼"]
    )

    uploaded_order_file = st.file_uploader(
        f"[{platform_choice}] 통합 발주서 업로드 (엑셀/파일)", 
        type=None, 
        key="up_order"
    )

    if st.button("🔄 발주서 분석 및 3개 공급처별 분할하기"):
        if not uploaded_order_file:
            st.warning("발주서 파일을 업로드해 주세요!")
        else:
            try:
                # 파일 읽기 (확장자 유연 대응)
                fname = uploaded_order_file.name.lower()
                if fname.endswith('.csv'):
                    df_order = pd.read_csv(uploaded_order_file)
                else:
                    try:
                        df_order = pd.read_excel(uploaded_order_file, engine='openpyxl')
                    except:
                        df_order = pd.read_excel(uploaded_order_file)

                zip_buffer = io.BytesIO()

                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    # 상품명/품목 컬럼 자동 탐색
                    prod_col = None
                    for col in df_order.columns:
                        if any(k in str(col) for k in ["상품명", "품명", "옵션", "상품"]):
                            prod_col = col
                            break

                    # 세 군데 공급처별 분할 로직
                    if prod_col:
                        # 1. 키스틱 공급처
                        df_kistic = df_order[df_order[prod_col].astype(str).str.contains("키스틱|어묵", na=False)]
                        if not df_kistic.empty:
                            b_kis = io.BytesIO()
                            df_kistic.to_excel(b_kis, index=False, engine="openpyxl")
                            zf.writestr("1_공급처_키스틱_발주서.xlsx", b_kis.getvalue())

                        # 2. 냉동식품 공급처
                        df_frozen = df_order[df_order[prod_col].astype(str).str.contains("만두|냉동|볶음밥", na=False)]
                        if not df_frozen.empty:
                            b_fro = io.BytesIO()
                            df_frozen.to_excel(b_fro, index=False, engine="openpyxl")
                            zf.writestr("2_공급처_냉동식품_발주서.xlsx", b_fro.getvalue())

                        # 3. 가람식품 공급처
                        df_garam = df_order[df_order[prod_col].astype(str).str.contains("어묵바|가람", na=False)]
                        if not df_garam.empty:
                            b_gar = io.BytesIO()
                            df_garam.to_excel(b_gar, index=False, engine="openpyxl")
                            zf.writestr("3_공급처_가람식품_발주서.xlsx", b_gar.getvalue())

                    # 원본 백업 파일 추가
                    b_bak = io.BytesIO()
                    df_order.to_excel(b_bak, index=False, engine="openpyxl")
                    zf.writestr(f"원본_{platform_choice}_통합발주서.xlsx", b_bak.getvalue())

                # 선택한 플랫폼 명칭으로 매출 데이터 자동 누적 기록
                total_cnt = len(df_order)
                est_revenue = total_cnt * 15000  # 건당 평균 추정 단가
                new_rec = pd.DataFrame([{
                    "날짜": datetime.datetime.now().strftime("%Y-%m-%d"),
                    "판매처": platform_choice,
                    "상품명": f"{platform_choice} 통합 발주 상품",
                    "수량": total_cnt,
                    "매출액": est_revenue,
                    "원가": int(est_revenue * 0.6),
                    "배송비": total_cnt * 3000,
                    "수수료": int(est_revenue * 0.1),
                    "순이익": int(est_revenue * 0.3)
                }])
                save_history(new_rec)

                zip_buffer.seek(0)
                st.success(f"✨ [{platform_choice}] 발주서가 3개 공급처별로 성공적으로 분할되었습니다! (매출 데이터 반영 완료)")
                st.download_button(
                    label="📥 3개 공급처별 분할 발주서 모음 (ZIP) 다운로드",
                    data=zip_buffer,
                    file_name=f"{platform_choice}_공급처별발주서모음_{datetime.datetime.now().strftime('%Y%m%d')}.zip",
                    mime="application/zip",
                )
            except Exception as e:
                st.error(f"파일 처리 중 오류가 발생했습니다: {e}")

# -------------------------------------------------------------------------
# 2탭: 플랫폼별 종합 매출 분석 대시보드
# -------------------------------------------------------------------------
with tab2:
    st.header("📈 플랫폼별 종합 매출 분석 대시보드")
    st.markdown("쿠팡, 스마트스토어, 올웨이즈 등 **판매처 플랫폼별로 구분된 매출 및 순이익 현황**을 비교 분석합니다.")

    history_df = load_history()
    if not history_df.empty:
        # 판매처 플랫폼별 요약 지표
        st.subheader("📊 플랫폼별 매출 및 순이익 비교")
        if "판매처" in history_df.columns:
            platform_summary = history_df.groupby("판매처")[["수량", "매출액", "순이익"]].sum().reset_index()
            # 보기 좋게 컬럼명 정돈
            platform_summary.columns = ["판매 플랫폼", "총 판매 수량", "총 매출액", "총 순이익"]
            st.dataframe(platform_summary, use_container_width=True)
        
        st.markdown("---")
        
        # 월간/전체 요약 메트릭
        history_df["날짜"] = pd.to_datetime(history_df["날짜"])
        history_df["년월"] = history_df["날짜"].dt.strftime("%Y-%m")
        cur_ym = datetime.datetime.now().strftime("%Y-%m")
        m_df = history_df[history_df["년월"] == cur_ym]

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(label=f"📅 {cur_ym} 이번 달 총 매출", value=f"{int(m_df['매출액'].sum()):,} 원")
        with c2:
            st.metric(label=f"✨ {cur_ym} 이번 달 총 순이익", value=f"{int(m_df['순이익'].sum()):,} 원")
        with c3:
            st.metric(label="🏆 전체 누적 총매출", value=f"{int(history_df['매출액'].sum()):,} 원")
        
        st.markdown("---")
        st.subheader("📋 플랫폼별 전체 거래 상세 내역")
        st.dataframe(history_df, use_container_width=True)
    else:
        st.info("아직 누적된 매출 데이터가 없습니다. 1단계에서 플랫폼별 발주서 파일을 업로드해 주세요.")
