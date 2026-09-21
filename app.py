import os
import datetime
import io
import zipfile
import pandas as pd
import streamlit as st

# 페이지 설정 및 디자인 테마
st.set_page_config(
    page_title="마켓지니 직원용 송장 및 매출 관리 앱", page_icon="🔒", layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button {
        background-color: #ff4b4b;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        height: 3em;
        width: 100%;
    }
    .auth-box {
        background-color: white;
        padding: 30px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        max-width: 400px;
        margin: 100px auto;
    }
    </style>
""", unsafe_allow_html=True)

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

# -------------------------------------------------------------------------
# 직원 전용 보안 로그인 시스템 (웹앱 형태)
# -------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("<div class='auth-box'>", unsafe_allow_html=True)
    st.title("🔒 직원 전용 로그인")
    st.markdown("인가된 직원만 접근할 수 있는 마켓지니 내부 앱입니다.")
    
    emp_id = st.text_input("직원 아이디")
    emp_pw = st.text_input("비밀번호", type="password")
    
    if st.button("로그인"):
        # 설정하고 싶으신 아이디와 비밀번호 (기본: admin / market1234)
        if emp_id == "admin" and emp_pw == "market1234":
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# -------------------------------------------------------------------------
# 로그인 성공 후 메인 앱 화면 (송장 생성 & 매출 관리 전용)
# -------------------------------------------------------------------------
st.title("🌟 마켓지니 직원용 송장 생성 & 매출 관리 웹앱")
st.markdown(
    "**1. 공급처 회신 송장 일괄 변환:** 공급처 회신 파일에서 고객명을 정확히 대조하여 마켓별 최종 송장 파일 자동 생성<br>"
    "**2. 매출 및 순이익 대시보드:** 누적 매출 및 수익 분석 데이터 관리",
    unsafe_allow_html=True,
)
st.markdown("---")

tab1, tab2 = st.tabs(["🚚 1단계: 공급처 회신 송장 일괄 변환", "📈 2단계: 종합 매출 & 순이익 대시보드"])

with tab1:
    st.header("🚚 공급처 회신 파일 -> 마켓별 최종 송장 업로드 파일 생성")
    st.markdown(
        "최초 올웨이즈 원본 발주서와 각 공급처 회신 파일을 올리시면, **고객명 기준**으로 "
        "송장을 정확히 매칭합니다. (가람식품도 올웨이즈 원본 양식 기준으로 송장 및 택배사 자동 매칭)"
    )

    up_orig_alw = st.file_uploader(
        "1. [필수] 최초 올웨이즈 원본 발주서 업로드 (엑셀)",
        type=["xlsx", "xls"],
        key="orig_alw",
    )

    st.markdown("---")
    col_ret1, col_ret2, col_ret3 = st.columns(3)
    with col_ret1:
        ret_kistic = st.file_uploader("키스틱 회신 파일 (2개 시트)", type=["xlsx", "xls"], key="ret_kis")
    with col_ret2:
        ret_frozen = st.file_uploader("냉동 회신 파일 (만두 등)", type=["xlsx", "xls"], key="ret_fro")
    with col_ret3:
        ret_garam = st.file_uploader("가람식품 회신 파일 (어묵바)", type=["xlsx", "xls"], key="ret_gar")

    if st.button("🛠️ 마켓 업로드용 송장 파일 일괄 변환하기"):
        if not up_orig_alw:
            st.warning("올웨이즈 원본 양식 매칭을 위해 '최초 올웨이즈 원본 발주서'를 반드시 업로드해 주세요!")
        else:
            df_orig_alw = pd.read_excel(up_orig_alw)
            zip_out = io.BytesIO()

            with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_DEFLATED) as zf:
                def map_invoice_by_name(df_target, df_return, name_col_ret, inv_col_ret):
                    if df_target is None or df_return is None or df_target.empty or df_return.empty:
                        return df_target

                    target_name_col = None
                    for c in ["수령인", "수취인명", "수령자이름"]:
                        if c in df_target.columns:
                            target_name_col = c
                            break

                    if not target_name_col or name_col_ret not in df_return.columns:
                        return df_target

                    inv_map = (
                        df_return.dropna(subset=[inv_col_ret])
                        .set_index(name_col_ret)[inv_col_ret]
                        .to_dict()
                    )

                    if "송장번호" not in df_target.columns:
                        df_target["송장번호"] = ""

                    for idx, row in df_target.iterrows():
                        c_name = str(row.get(target_name_col, "")).strip()
                        if c_name in inv_map:
                            df_target.at[idx, "송장번호"] = str(inv_map[c_name])

                    return df_target

                # 1. 키스틱 회신 처리
                if ret_kistic:
                    xls_kis = pd.ExcelFile(ret_kistic)
                    sheets = xls_kis.sheet_names
                    df_kis_target = (
                        pd.read_excel(ret_kistic, sheet_name=sheets[1])
                        if len(sheets) >= 2
                        else pd.read_excel(ret_kistic, sheet_name=sheets[0])
                    )

                    target_prod_col = None
                    for c in df_kis_target.columns:
                        if any(w in c for w in ["상품명", "품명", "옵션"]):
                            target_prod_col = c
                            break

                    if target_prod_col:
                        df_kis_target = df_kis_target[
                            ~df_kis_target[target_prod_col].astype(str).str.contains("어묵", na=False)
                        ]

                    b_kis = io.BytesIO()
                    df_kis_target.to_excel(b_kis, index=False, engine="openpyxl")
                    zf.writestr("키스틱_송장업로드용_정리완료.xlsx", b_kis.getvalue())

                    k_name_col, k_inv_col = None, None
                    for c in df_kis_target.columns:
                        if any(w in c for w in ["수령", "성명", "받는분", "고객"]):
                            k_name_col = c
                        if any(w in c for w in ["송장", "운송장"]):
                            k_inv_col = c

                    if k_name_col and k_inv_col:
                        df_matched_kis = map_invoice_by_name(
                            df_orig_alw.copy(), df_kis_target, k_name_col, k_inv_col
                        )
                        b_alw_kis = io.BytesIO()
                        df_matched_kis.dropna(subset=["송장번호"]).to_excel(
                            b_alw_kis, index=False, engine="openpyxl"
                        )
                        zf.writestr("올웨이즈_키스틱상품_송장업로드용.xlsx", b_alw_kis.getvalue())

                # 2. 냉동 회신 처리
                if ret_frozen:
                    df_fro_ret = pd.read_excel(ret_frozen)
                    f_name_col, f_inv_col = None, None
                    for c in df_fro_ret.columns:
                        if any(w in c for w in ["수령", "성명", "받는분", "고객"]):
                            f_name_col = c
                        if any(w in c for w in ["송장", "운송장"]):
                            f_inv_col = c

                    if f_name_col and f_inv_col:
                        df_matched_fro = map_invoice_by_name(
                            df_orig_alw.copy(), df_fro_ret, f_name_col, f_inv_col
                        )
                        b_fro = io.BytesIO()
                        df_matched_fro.dropna(subset=["송장번호"]).to_excel(
                            b_fro, index=False, engine="openpyxl"
                        )
                        zf.writestr("올웨이즈_냉동상품_송장업로드용.xlsx", b_fro.getvalue())

                # 3. 가람식품 회신 처리
                if ret_garam:
                    df_gar_ret = pd.read_excel(ret_garam)
                    g_name_col, g_inv_col = None, None
                    for c in df_gar_ret.columns:
                        if any(w in c for w in ["수령", "성명", "받는분", "고객"]):
                            g_name_col = c
                        if any(w in c for w in ["송장", "운송장"]):
                            g_inv_col = c

                    if g_name_col and g_inv_col:
                        df_matched_gar = map_invoice_by_name(
                            df_orig_alw.copy(), df_gar_ret, g_name_col, g_inv_col
                        )

                        for c in df_matched_gar.columns:
                            if any(w in c for w in ["택배", "배송사", "택배사"]):
                                df_matched_gar[c] = "롯데택배"

                        b_alw_gar = io.BytesIO()
                        df_matched_gar.dropna(subset=["송장번호"]).to_excel(
                            b_alw_gar, index=False, engine="openpyxl"
                        )
                        zf.writestr("올웨이즈_가람식품상품_송장업로드용.xlsx", b_alw_gar.getvalue())

            zip_out.seek(0)
            st.success("✨ 키스틱 어묵바 제외 및 가람식품 올웨이즈 양식 변환 완료!")
            st.download_button(
                label="📥 최종 마켓 업로드용 송장 파일 모음 (ZIP) 다운로드",
                data=zip_out,
                file_name=f"마켓지니_최종송장파일모음_{datetime.datetime.now().strftime('%Y%m%d')}.zip",
                mime="application/zip",
            )

with tab2:
    st.header("📈 종합 매출 & 순이익 대시보드")
    history_df = load_history()
    if not history_df.empty:
        history_df["날짜"] = pd.to_datetime(history_df["날짜"])
        history_df["년월"] = history_df["날짜"].dt.strftime("%Y-%m")
        cur_ym = datetime.datetime.now().strftime("%Y-%m")
        m_df = history_df[history_df["년월"] == cur_ym]

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(
                label=f"📅 {cur_ym} 이번 달 누적 매출",
                value=f"{int(m_df['매출액'].sum()):,} 원",
            )
        with c2:
            st.metric(
                label=f"✨ {cur_ym} 이번 달 누적 순이익",
                value=f"{int(m_df['순이익'].sum()):,} 원",
            )
        with c3:
            st.metric(
                label="🏆 전체 누적 총매출",
                value=f"{int(history_df['매출액'].sum()):,} 원",
            )
        
        st.markdown("---")
        st.subheader("📋 전체 매출 내역 데이터")
        st.dataframe(history_df, use_container_width=True)
    else:
        st.info("저장된 매출 데이터가 아직 없습니다. (이전 발주서 연동 내역이 누적되면 여기에 표시됩니다.)")