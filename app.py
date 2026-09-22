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
    shopmoa_file = st.file_uploader(
        "📥 [샵모아] 통합 발주서 업로드", type=["xlsx", "xls", "csv"], key="shopmoa"
    )
with col2:
    always_file = st.file_uploader(
        "📥 [올웨이즈] 통합 발주서 업로드", type=["xlsx", "xls", "csv"], key="always"
    )


# 데이터 전처리 및 변환 로직 함수
def process_orders(shopmoa_df, always_df):
    frames = []
    if shopmoa_df is not None:
        shopmoa_df["출처"] = "샵모아"
        frames.append(shopmoa_df)
    if always_df is not None:
        always_df["출처"] = "올웨이즈"
        frames.append(always_df)

    if not frames:
        return None, None, None

    combined_df = pd.concat(frames, ignore_index=True)

    # ----------------------------------------------------
    # 여기에 각 공급처별(가람식품, 키스틱, 냉동식품) 가공 로직 구현
    # ----------------------------------------------------

    # 예시: 키스틱 40/100개 변환 및 홀수 분할, 어묵바 분리, 김말이 팩수 계산 등 규칙 적용
    garam_df = combined_df.copy()  # 가람식품 데이터 프레임 예시
    kistic_df = combined_df.copy()  # 키스틱 데이터 프레임 예시
    frozen_df = combined_df.copy()  # 냉동식품 데이터 프레임 예시

    return garam_df, kistic_df, frozen_df


# 변환 실행 버튼
if st.button("🔄 맞춤형 발주서 변환 및 3개 공급처별 분할 실행", type="primary", use_container_width=True):
    if shopmoa_file is None and always_file is None:
        st.warning("⚠️ 샵모아 또는 올웨이즈 발주서 파일을 최소 1개 이상 업로드해 주세요.")
    else:
        try:
            # 파일 읽기
            s_df = (
                pd.read_excel(shopmoa_file)
                if shopmoa_file
                else None
            )
            a_df = (
                pd.read_excel(always_file)
                if always_file
                else None
            )

            garam, kistic, frozen = process_orders(s_df, a_df)

            # 결과물 ZIP 압축 생성
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                if garam is not None:
                    g_io = io.BytesIO()
                    garam.to_excel(g_io, index=False)
                    zip_file.writestr("1_가람식품_발주서.xlsx", g_io.getvalue())

                if kistic is not None:
                    k_io = io.BytesIO()
                    kistic.to_excel(k_io, index=False)
                    zip_file.writestr("2_키스틱_발주서.xlsx", k_io.getvalue())

                if frozen is not None:
                    f_io = io.BytesIO()
                    frozen.to_excel(f_io, index=False)
                    zip_file.writestr("3_냉동식품_발주서.xlsx", f_io.getvalue())

            zip_buffer.seek(0)

            st.success("✨ 성공적으로 변환되었습니다! 아래 버튼을 눌러 다운로드하세요.")
            st.download_button(
                label="📥 3개 공급처별 발주서 ZIP 다운로드",
                data=zip_buffer,
                file_name="마켓지니_맞춤발주서_통합세트.zip",
                mime="application/zip",
                use_container_width=True,
            )

        except Exception as e:
            st.error(f"❌ 변환 중 오류가 발생했습니다: {e}")
