import datetime
import io
import zipfile
import pandas as pd
import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="마켓지니 발주서 자동 분할 및 송장 변환 프로그램",
    page_icon="📦",
    layout="wide",
)

st.title("📦 마켓지니 발주서 자동 분할 및 송장 관리 프로그램")
st.markdown(
    "**1. 발주서 분할 기능:** 최초 다운로드한 통합 발주서를 각 공급처별(키스틱, 냉동, 가람식품 등) 양식에 맞게 자동으로 분할합니다.<br>"
    "**2. 송장 변환 기능:** 공급처 회신 파일에서 고객명을 대조하여 최종 송장 업로드 파일을 생성합니다.",
    unsafe_allow_html=True,
)
st.markdown("---")

tab1, tab2 = st.tabs(
    ["📥 1단계: 통합 발주서 -> 공급처별 분할", "🚚 2단계: 회신 송장 일괄 변환"]
)

# -------------------------------------------------------------------------
# 1탭: 통합 발주서 -> 공급처별 분할 기능 (이전 개발 단계 복원)
# -------------------------------------------------------------------------
with tab1:
    st.header("📥 통합 발주서 공급처별 자동 분할")
    st.markdown(
        "마켓에서 다운로드한 통합 발주서 엑셀 파일을 업로드하시면, "
        "상품 품목이나 공급처별 기준에 맞춰 자동으로 분류된 발주서 파일들을 ZIP 파일로 생성해 드립니다."
    )

    uploaded_order_file = st.file_uploader(
        "통합 발주서 엑셀 파일 업로드", type=["xlsx", "xls"], key="split_order"
    )

    if st.button("🔄 발주서 분할 파일 생성하기"):
        if uploaded_order_file is None:
            st.warning("분할할 통합 발주서 파일을 업로드해 주세요.")
        else:
            try:
                df_order = pd.read_excel(uploaded_order_file)
                zip_buffer = io.BytesIO()

                with zipfile.ZipFile(
                    zip_buffer, "w", zipfile.ZIP_DEFLATED
                ) as zf:
                    # 상품명/품목 컬럼 탐색
                    prod_col = None
                    for col in df_order.columns:
                        if any(
                            keyword in col
                            for keyword in ["상품명", "품명", "옵션", "상품"]
                        ):
                            prod_col = col
                            break

                    if prod_col:
                        # 1. 키스틱 관련 상품 발주서
                        df_kistic = df_order[
                            df_order[prod_col].astype(str).str.contains("키스틱|어묵", na=False)
                        ]
                        if not df_kistic.empty:
                            b_kis = io.BytesIO()
                            df_kistic.to_excel(
                                b_kis, index=False, engine="openpyxl"
                            )
                            zf.writestr(
                                "공급처_키스틱_발주서.xlsx", b_kis.getvalue()
                            )

                        # 2. 냉동 상품 발주서 (만두 등)
                        df_frozen = df_order[
                            df_order[prod_col].astype(str).str.contains("만두|냉동|볶음밥", na=False)
                        ]
                        if not df_frozen.empty:
                            b_fro = io.BytesIO()
                            df_frozen.to_excel(
                                b_fro, index=False, engine="openpyxl"
                            )
                            zf.writestr(
                                "공급처_냉동식품_발주서.xlsx", b_fro.getvalue()
                            )

                        # 3. 가람식품 (어묵바 등)
                        df_garam = df_order[
                            df_order[prod_col].astype(str).str.contains("어묵바|가람", na=False)
                        ]
                        if not df_garam.empty:
                            b_gar = io.BytesIO()
                            df_garam.to_excel(
                                b_gar, index=False, engine="openpyxl"
                            )
                            zf.writestr(
                                "공급처_가람식품_발주서.xlsx", b_gar.getvalue()
                            )
                    
                    # 만약 특정 키워드 분류에 걸리지 않거나 전체 원본도 포함 필요시 기본 백업용 포함
                    b_all = io.BytesIO()
                    df_order.to_excel(b_all, index=False, engine="openpyxl")
                    zf.writestr("전체_통합_발주서_백업.xlsx", b_all.getvalue())

                zip_buffer.seek(0)
                st.success("✨ 발주서가 공급처별로 성공적으로 분할되었습니다!")
                st.download_button(
                    label="📥 공급처별 분할 발주서 모음 (ZIP) 다운로드",
                    data=zip_buffer,
                    file_name=f"분할발주서모음_{datetime.datetime.now().strftime('%Y%m%d')}.zip",
                    mime="application/zip",
                )
            except Exception as e:
                st.error(f"파일 처리 중 오류가 발생했습니다: {e}")

# -------------------------------------------------------------------------
# 2탭: 공급처 회신 송장 일괄 변환 기능
# -------------------------------------------------------------------------
with tab2:
    st.header("🚚 공급처 회신 파일 -> 마켓별 최종 송장 업로드 파일 생성")
    st.markdown(
        "최초 원본 발주서와 각 공급처 회신 파일을 올리시면, **고객명 기준**으로 "
        "송장을 정확히 매칭하여 마켓 업로드용 파일로 변환해 드립니다."
    )

    up_orig_alw = st.file_uploader(
        "1. [필수] 최초 원본 발주서 업로드 (엑셀)",
        type=["xlsx", "xls"],
        key="orig_alw",
    )

    st.markdown("---")
    col_ret1, col_ret2, col_ret3 = st.columns(3)
    with col_ret1:
        ret_kistic = st.file_uploader(
            "키스틱 회신 파일", type=["xlsx", "xls"], key="ret_kis"
        )
    with col_ret2:
        ret_frozen = st.file_uploader(
            "냉동 회신 파일", type=["xlsx", "xls"], key="ret_fro"
        )
    with col_ret3:
        ret_garam = st.file_uploader(
            "가람식품 회신 파일", type=["xlsx", "xls"], key="ret_gar"
        )

    if st.button("🛠️ 마켓 업로드용 송장 파일 일괄 변환하기"):
        if not up_orig_alw:
            st.warning("원본 발주서를 반드시 업로드해 주세요!")
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

                # 키스틱 회신 처리
                if ret_kistic:
                    xls_kis = pd.ExcelFile(ret_kistic)
                    sheets = xls_kis.sheet_names
                    df_kis_target = (
                        pd.read_excel(ret_kistic, sheet_name=sheets[1])
                        if len(sheets) >= 2
                        else pd.read_excel(ret_kistic, sheet_name=sheets[0])
                    )
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
                        zf.writestr("키스틱상품_송장업로드용.xlsx", b_alw_kis.getvalue())

                # 냉동 회신 처리
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
                        zf.writestr("냉동상품_송장업로드용.xlsx", b_fro.getvalue())

                # 가람식품 회신 처리
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
                        zf.writestr("가람식품상품_송장업로드용.xlsx", b_alw_gar.getvalue())

            zip_out.seek(0)
            st.success("✨ 송장 변환 작업이 완료되었습니다!")
            st.download_button(
                label="📥 최종 송장 파일 모음 (ZIP) 다운로드",
                data=zip_out,
                file_name=f"최종송장파일모음_{datetime.datetime.now().strftime('%Y%m%d')}.zip",
                mime="application/zip",
            )
