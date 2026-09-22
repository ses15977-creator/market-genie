import io
import zipfile
import pandas as pd
import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="마켓지니 스마트 발주서 변환기",
    page_icon="📦",
    layout="wide",
)

st.title("📦 마켓지니 샵모아 & 올웨이즈 맞춤 발주서 변환기")
st.markdown(
    "**샵모아**와 **올웨이즈** 발주서 파일을 동시에(또는 개별로) 업로드하시면, "
    "공급처별 맞춤 규칙(어묵바 합배송 분리, 키스틱 40/100개 변환 및 홀수 분할, 김말이 팩수 배수 계산)을 적용하여 "
    "**1. 가람식품, 2. 키스틱, 3. 냉동식품** 3가지 발주서로 분할 압축해 드립니다.",
    unsafe_allow_html=True,
)
st.markdown("---")

# 파일 업로드 영역 (샵모아 / 올웨이즈 동시 지원)
col1, col2 = st.columns(2)
with col1:
    shopmoa_file = st.file_uploader("📥 [샵모아] 통합 발주서 업로드", type=["xlsx", "xls", "csv"], key="shopmoa")
with col2:
    always_file = st.file_uploader("📥 [올웨이즈] 통합 발주서 업로드", type=["xlsx", "xls", "csv"], key="always")

if st.button("🔄 맞춤형 발주서 변환 및 3개 공급처별 분할 실행", type="primary", use_container_width=True):
    if not shopmoa_file and not always_file:
        st.warning("샵모아 또는 올웨이즈 발주서 파일을 최소 1개 이상 업로드해 주세요!")
    else:
        try:
            dfs = []
            
            # 1. 샵모아 파일 읽기
            if shopmoa_file:
                if shopmoa_file.name.lower().endswith('.csv'):
                    df_s = pd.read_csv(shopmoa_file)
                else:
                    df_s = pd.read_excel(shopmoa_file, engine='openpyxl')
                df_s["유입플랫폼"] = "샵모아"
                dfs.append(df_s)

            # 2. 올웨이즈 파일 읽기
            if always_file:
                if always_file.name.lower().endswith('.csv'):
                    df_a = pd.read_csv(always_file)
                else:
                    df_a = pd.read_excel(always_file, engine='openpyxl')
                df_a["유입플랫폼"] = "올웨이즈"
                dfs.append(df_a)

            # 통합 데이터프레임 생성
            df_order = pd.concat(dfs, ignore_index=True)

            # 컬럼 자동 탐색
            name_col = next((c for c in ["수령인", "수취인명", "받는분", "고객명"] if c in df_order.columns), None)
            opt_col = next((c for c in ["옵션명", "상품옵션", "주문옵션"] if c in df_order.columns), None)
            prod_col = next((c for c in ["상품명", "품명"] if c in df_order.columns), None)
            qty_col = next((c for c in ["수량", "주문수량", "구매수량"] if c in df_order.columns), None)

            processed_garam_rows = []
            processed_kistic_rows = []
            processed_frozen_rows = []

            for _, row in df_order.iterrows():
                platform = row.get("유입플랫폼", "샵모아")
                
                # 올웨이즈는 옵션명 우선, 샵모아는 상품명/옵션명 활용
                opt_val = str(row.get(opt_col, "")) if opt_col and pd.notna(row.get(opt_col)) else ""
                base_prod = str(row.get(prod_col, "")) if prod_col and pd.notna(row.get(prod_col)) else ""
                
                # 비교를 위한 통합 텍스트
                check_text = f"{opt_val} {base_prod}"
                raw_qty = int(row.get(qty_col, 1)) if qty_col and pd.notna(row.get(qty_col)) else 1

                # -------------------------------------------------------------
                # 1. 가람식품 (부산어묵바 4가지) 규칙 적용
                # -------------------------------------------------------------
                if any(k in check_text for k in ["어묵바", "부산어묵바", "오리지날", "매콤달콤", "오징어야채", "체다치즈"]):
                    target_name = "오리지날 부산어묵바"
                    if "매콤달콤" in check_text:
                        target_name = "매콤달콤 부산어묵바"
                    elif "오징어야채" in check_text:
                        target_name = "오징어야채 부산어묵바"
                    elif "체다치즈" in check_text:
                        target_name = "체다치즈 부산어묵바"

                    # 합배송 불가: 동일 옵션 2개 이상이면 수량만큼 행 분리 및 수령인 뒤에 번호 붙이기 (고객명_1, 고객명_2)
                    for i in range(raw_qty):
                        new_row = row.copy()
                        if name_col and name_col in new_row and raw_qty > 1:
                            new_row[name_col] = f"{row[name_col]}_{i+1}"
                        if opt_col:
                            new_row[opt_col] = target_name
                        if prod_col:
                            new_row[prod_col] = target_name
                        if qty_col:
                            new_row[qty_col] = 1
                        processed_garam_rows.append(new_row)

                # -------------------------------------------------------------
                # 2. 키스틱류 규칙 적용 (40개 / 100개 변환 및 홀수 분할)
                # -------------------------------------------------------------
                elif "키ส틱" in check_text:
                    # 40개짜리 상품 주문인 경우
                    if "40" in check_text:
                        # 수량 2개 구매 시 -> 100개짜리 1세트로 전환
                        sets_of_100 = raw_qty // 2
                        remainder_40 = raw_qty % 2

                        if sets_of_100 > 0:
                            r1 = row.copy()
                            if opt_col: r1[opt_col] = "키ส틱 15g x 100개"
                            if prod_col: r1[prod_col] = "키ส틱 15g x 100개"
                            if qty_col: r1[qty_col] = sets_of_100
                            processed_kistic_rows.append(r1)

                        if remainder_40 > 0:
                            r2 = row.copy()
                            if opt_col: r2[opt_col] = "키ส틱 15g x 40개"
                            if prod_col: r2[prod_col] = "키스틱 15g x 40개"
                            if qty_col: r2[qty_col] = remainder_40
                            processed_kistic_rows.append(r2)

                    # 100개짜리 상품 주문인 경우 (수량 그대로 유지)
                    elif "100" in check_text:
                        r = row.copy()
                        if opt_col: r[opt_col] = "키ส틱 15g x 100개"
                        if prod_col: r[prod_col] = "키ส틱 15g x 100개"
                        if qty_col: r[qty_col] = raw_qty
                        processed_kistic_rows.append(r)
                    else:
                        processed_kistic_rows.append(row)

                # -------------------------------------------------------------
                # 3. 냉동식품류 규칙 적용 (만두 및 김말이튀김)
                # -------------------------------------------------------------
                elif any(k in check_text for k in ["만두", "고추잡채", "김말이"]):
                    if "김말이" in check_text:
                        # 김말이튀김: 기본 1세트 = 3팩 (주문수량 * 3)
                        r = row.copy()
                        if opt_col: r[opt_col] = "김말이튀김400g"
                        if prod_col: r[prod_col] = "김말이튀김400g"
                        if qty_col: r[qty_col] = raw_qty * 3
                        processed_frozen_rows.append(r)
                    else:
                        # 고추잡채군만두 등 (수량 그대로 반영)
                        r = row.copy()
                        if qty_col: r[qty_col] = raw_qty
                        processed_frozen_rows.append(r)

            # 결과 데이터프레임 생성
            df_garam = pd.DataFrame(processed_garam_rows) if processed_garam_rows else pd.DataFrame(columns=df_order.columns)
            df_kistic = pd.DataFrame(processed_kistic_rows) if processed_kistic_rows else pd.DataFrame(columns=df_order.columns)
            df_frozen = pd.DataFrame(processed_frozen_rows) if processed_frozen_rows else pd.DataFrame(columns=df_order.columns)

            # ZIP 압축 파일 생성
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

                # 원본 통합 백업
                b_bak = io.BytesIO()
                df_order.to_excel(b_bak, index=False, engine="openpyxl")
                zf.writestr("원본_통합발주서_백업.xlsx", b_bak.getvalue())

            zip_buffer.seek(0)
            st.success("✨ 맞춤형 발주서 변환이 성공적으로 완료되었습니다!")
            st.download_button(
                label="📥 3개 공급처별 맞춤 발주서 엑셀 모음 (ZIP) 다운로드",
                data=zip_buffer,
                file_name=f"마켓지니_맞춤발주서_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.zip",
                mime="application/zip",
                use_container_width=True,
            )

        except Exception as e:
            st.error(f"파일 처리 중 오류가 발생했습니다: {e}")
