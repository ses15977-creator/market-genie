import datetime
import io
import zipfile
import os
import pandas as pd
import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="마켓지니 맞춤형 발주서 변환 프로그램",
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
        "날짜", "플랫폼", "상품명", "수량", "매출액", "원가", "배송비", "수수료", "순이익"
    ])

def save_history(new_row_df):
    df = load_history()
    df = pd.concat([df, new_row_df], ignore_index=True)
    df.to_csv(DB_FILE, index=False)

st.title("📦 마켓지니 맞춤형 발주서 변환 및 매출 분석 프로그램")
st.markdown(
    "**1단계:** 샵모아 및 올웨이즈 발주서를 업로드하여 **가람식품(어묵바), 키스틱, 냉동식품** 맞춤 규칙(합배송 불가 분리, 수량 치환 및 배수 계산)에 맞게 3개 공급처별 엑셀 양식으로 완벽 변환<br>"
    "**2단계:** 플랫폼별 상세 매출 및 순이익 분석 대시보드 확인",
    unsafe_allow_html=True,
)
st.markdown("---")

tab1, tab2 = st.tabs(
    ["📥 1단계: 맞춤형 발주서 변환 및 3분할", "📈 2단계: 플랫폼별 매출 분석 대시보드"]
)

# -------------------------------------------------------------------------
# 1탭: 맞춤형 발주서 변환 및 3개 공급처별 분할 다운로드
# -------------------------------------------------------------------------
with tab1:
    st.header("📥 맞춤형 발주서 변환 및 3개 공급처별 분할 다운로드")
    st.markdown(
        "샵모아 또는 올웨이즈 발주서 파일을 업로드해 주세요. "
        "어묵바(합배송 불가 분리), 키스틱(40개/100개 변환 및 홀수 분할), 냉동만두/김말이(팩수 배수 계산) 규칙이 자동 적용됩니다."
    )

    platform_choice = st.selectbox(
        "🏷️ 업로드할 발주서의 판매 플랫폼 선택",
        ["샵모아", "올웨이즈", "쿠팡", "네이버 스마트스토어"]
    )

    uploaded_order_file = st.file_uploader(
        f"[{platform_choice}] 통합 발주서 파일 업로드", 
        type=None, 
        key="up_order_custom"
    )

    if st.button("🔄 맞춤형 발주서 분석 및 변환 실행"):
        if not uploaded_order_file:
            st.warning("발주서 파일을 업로드해 주세요!")
        else:
            try:
                # 파일 읽기 유연 대응
                fname = uploaded_order_file.name.lower()
                if fname.endswith('.csv'):
                    df_order = pd.read_csv(uploaded_order_file)
                else:
                    try:
                        df_order = pd.read_excel(uploaded_order_file, engine='openpyxl')
                    except:
                        df_order = pd.read_excel(uploaded_order_file)

                # 컬럼 매핑 보정 (수령인, 옵션/상품명 탐색)
                name_col = None
                for c in ["수령인", "수취인명", "받는분", "고객명"]:
                    if c in df_order.columns:
                        name_col = c
                        break

                opt_col = None
                for c in ["옵션명", "상품옵션", "주문옵션", "상품명", "품명"]:
                    if c in df_order.columns:
                        opt_col = c
                        break

                qty_col = None
                for c in ["수량", "주문수량", "구매수량"]:
                    if c in df_order.columns:
                        qty_col = c
                        break

                processed_garam_rows = []
                processed_kistic_rows = []
                processed_frozen_rows = []

                for _, row in df_order.iterrows():
                    # 올웨이즈는 옵션명 우선, 샵모아는 상품명/옵션명 혼용 대응
                    opt_val = str(row.get(opt_col, "")) if opt_col else ""
                    raw_qty = int(row.get(qty_col, 1)) if qty_col and pd.notna(row.get(qty_col)) else 1
                    base_name = str(row.get("상품명", "")) if "상품명" in df_order.columns else opt_val

                    # ---------------------------------------------------------
                    # 규칙 1: 가람식품 (부산어묵바 4가지)
                    # ---------------------------------------------------------
                    if any(k in opt_val or k in base_name for k in ["어묵바", "부산어묵바", "오리지날", "매콤달콤", "오징어야채", "체다치즈"]):
                        target_name = "오리지날 부산어묵바"
                        if "매콤달콤" in opt_val or "매콤달콤" in base_name:
                            target_name = "매콤달콤 부산어묵바"
                        elif "오징어야채" in opt_val or "오징어야채" in base_name:
                            target_name = "오징어야채 부산어묵바"
                        elif "체다치즈" in opt_val or "체다치즈" in base_name:
                            target_name = "체다치즈 부산어묵바"

                        # 합배송 불가: 동일 옵션 2개 이상이면 수량만큼 행을 쪼개고 이름 뒤에 번호 붙이기 (예: 고객명_1, 고객명_2)
                        for i in range(raw_qty):
                            new_row = row.copy()
                            if name_col and name_col in new_row:
                                if raw_qty > 1:
                                    new_row[name_col] = f"{row[name_col]}_{i+1}"
                            if opt_col:
                                new_row[opt_col] = target_name
                            if "상품명" in new_row:
                                new_row["상품명"] = target_name
                            if qty_col:
                                new_row[qty_col] = 1
                            processed_garam_rows.append(new_row)

                    # ---------------------------------------------------------
                    # 규칙 2: 키스틱류 (40개 / 100개 변환 및 홀수 분할)
                    # ---------------------------------------------------------
                    elif "키ส틱" in opt_val or "키스틱" in base_name:
                        # 40개짜리 구매 건 처리
                        if "40" in opt_val or "40개" in opt_val:
                            total_40_qty = raw_qty * 2  # 예: 40개짜리 1개 = 총 40개 분량 / 만약 40개짜리 2개면 100개짜리로 전환 등
                            # 요청 사항: "키스틱 15g x 40개 상품을 수량 2개 구매하는 경우 -> 키스틱 15g x 100개, 수량 1세트로 수정"
                            # 즉, 40개짜리 2개 = 100개짜리 1개
                            sets_of_100 = raw_qty // 2
                            remainder_40 = raw_qty % 2

                            if sets_of_100 > 0:
                                r1 = row.copy()
                                if opt_col: r1[opt_col] = "키스틱 15g x 100개"
                                if "상품명" in r1: r1["상품명"] = "키스틱 15g x 100개"
                                if qty_col: r1[qty_col] = sets_of_100
                                processed_kistic_rows.append(r1)

                            if remainder_40 > 0:
                                r2 = row.copy()
                                if opt_col: r2[opt_col] = "키스틱 15g x 40개"
                                if "상품명" in r2: r2["상품명"] = "키스틱 15g x 40개"
                                if qty_col: r2[qty_col] = remainder_40
                                processed_kistic_rows.append(r2)

                        # 100개짜리 구매 건 처리 (그대로 반영)
                        elif "100" in opt_val or "100개" in opt_val:
                            r = row.copy()
                            if opt_col: r[opt_col] = "키스틱 15g x 100개"
                            if "상품명" in r: r["상품명"] = "키스틱 15g x 100개"
                            if qty_col: r[qty_col] = raw_qty
                            processed_kistic_rows.append(r)
                        else:
                            processed_kistic_rows.append(row)

                    # ---------------------------------------------------------
                    # 규칙 3: 냉동식품류 (만두 및 김말이튀김)
                    # ---------------------------------------------------------
                    elif any(k in opt_val or k in base_name for k in ["만두", "고추잡채", "김말이"]):
                        if "김말이" in opt_val or "김말이" in base_name:
                            # 김말이튀김 기본 1세트 = 400g x 3팩 (주문수량 * 3배)
                            r = row.copy()
                            if opt_col: r[opt_col] = "김말이튀김400g"
                            if "상품명" in r: r["상품명"] = "김말이튀김400g"
                            if qty_col: r[qty_col] = raw_qty * 3
                            processed_frozen_rows.append(r)
                        else:
                            # 고추잡채군만두 등 기타 냉동만두 (기존 수량 그대로)
                            r = row.copy()
                            if qty_col: r[qty_col] = raw_qty
                            processed_frozen_rows.append(r)

                # 데이터프레임 변환
                df_garam = pd.DataFrame(processed_garam_rows) if processed_garam_rows else pd.DataFrame(columns=df_order.columns)
                df_kistic = pd.DataFrame(processed_kistic_rows) if processed_kistic_rows else pd.DataFrame(columns=df_order.columns)
                df_frozen = pd.DataFrame(processed_frozen_rows) if processed_frozen_rows else pd.DataFrame(columns=df_order.columns)

                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    if not df_garam.empty:
                        b1 = io.BytesIO()
                        df_garam.to_excel(b1, index=False, engine="openpyxl")
                        zf.writestr("1_가람식품_부산어묵바_발주서.xlsx", b1.getvalue())

                    if not df_kistic.empty:
                        b2 = io.BytesIO()
                        df_kistic.to_excel(b2, index=False, engine="openpyxl")
                        zf.writestr("2_키스틱_발주서.xlsx", b2.getvalue())

                    if not df_frozen.empty:
                        b3 = io.BytesIO()
                        df_frozen.to_excel(b3, index=False, engine="openpyxl")
                        zf.writestr("3_냉동식품_만두김말이_발주서.xlsx", b3.getvalue())

                    # 원본 백업
                    b_bak = io.BytesIO()
                    df_order.to_excel(b_bak, index=False, engine="openpyxl")
                    zf.writestr(f"원본_{platform_choice}_통합발주서.xlsx", b_bak.getvalue())

                # 매출 데이터 누적 기록
                total_cnt = len(df_order)
                est_revenue = total_cnt * 15000  
                new_rec = pd.DataFrame([{
                    "날짜": datetime.datetime.now().strftime("%Y-%m-%d"),
                    "판매처": platform_choice,
                    "상품명": f"{platform_choice} 맞춤 발주 통합",
                    "수량": total_cnt,
                    "매출액": est_revenue,
                    "원가": int(est_revenue * 0.6),
                    "배송비": total_cnt * 3000,
                    "수수료": int(est_revenue * 0.1),
                    "순이익": int(est_revenue * 0.3)
                }])
                save_history(new_rec)

                zip_buffer.seek(0)
                st.success(f"✨ [{platform_choice}] 맞춤형 발주서 변환 및 3개 공급처 분할 완료!")
                st.download_button(
                    label="📥 3개 공급처별 맞춤 발주서 엑셀 모음 (ZIP) 다운로드",
                    data=zip_buffer,
                    file_name=f"{platform_choice}_맞춤분할발주서_{datetime.datetime.now().strftime('%Y%m%d')}.zip",
                    mime="application/zip",
                )
            except Exception as e:
                st.error(f"파일 처리 중 오류가 발생했습니다: {e}")

# -------------------------------------------------------------------------
# 2탭: 플랫폼별 종합 매출 분석 대시보드
# -------------------------------------------------------------------------
with tab2:
    st.header("📈 플랫폼별 종합 매출 분석 대시보드")
    st.markdown("샵모아, 올웨이즈, 쿠팡, 스마트스토어 등 **판매처 플랫폼별 누적 매출 및 순이익 현황**을 비교 분석합니다.")

    history_df = load_history()
    if not history_df.empty:
        st.subheader("📊 플랫폼별 매출 및 순이익 요약")
        if "판매처" in history_df.columns:
            platform_summary = history_df.groupby("판매처")[["수량", "매출액", "순이익"]].sum().reset_index()
            platform_summary.columns = ["판매 플랫폼", "총 판매 수량", "총 매출액", "총 순이익"]
            st.dataframe(platform_summary, use_container_width=True)
        
        st.markdown("---")
        
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
        st.subheader("📋 전체 거래 상세 내역")
        st.dataframe(history_df, use_container_width=True)
    else:
        st.info("아직 누적된 매출 데이터가 없습니다. 1단계에서 발주서 파일을 업로드해 주세요.")
