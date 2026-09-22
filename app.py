import io
import zipfile
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="마켓지니 스마트 발주서 변환기", page_icon="📦", layout="centered"
)

st.title("📦 마켓지니 스마트 발주서 변환기")
st.write(
    "샵모아와 올웨이즈 발주서 파일을 업로드한 후 실행 버튼을 누르면, 3개 공급처별 발주서가 담긴 ZIP 압축파일을 생성합니다."
)

st.markdown("---")

# 1. 파일 업로드 섹션
st.subheader("1. 발주서 파일 업로드")
shopmoa_file = st.file_uploader(
    "샵모아 발주서 파일 업로드 (.xlsx)", type=["xlsx", "xls"], key="shopmoa"
)
always_file = st.file_uploader(
    "올웨이즈 발주서 파일 업로드 (.xlsx)", type=["xlsx", "xls"], key="always"
)


def process_custom_orders(shopmoa_df, always_df):
  frames = []

  # 샵모아 데이터 표준화
  if shopmoa_df is not None and not shopmoa_df.empty:
    s_df = shopmoa_df.copy()
    s_df["수령자이름"] = s_df.get("수취인명", "")
    s_df["수령자전화"] = s_df.get("수취인 전화번호", "")
    s_df["수령자휴대폰"] = s_df.get("수취인 핸드폰번호", "")
    s_df["수령자우편번호"] = s_df.get("우편번호", "")
    s_df["수령자주소"] = s_df.get("수취인주소", "")
    s_df["상품명_원본"] = s_df.get("상품명", "")
    s_df["옵션_원본"] = s_df.get("옵션", "")
    s_df["상품수량"] = pd.to_numeric(s_df.get("수량", 1), errors="coerce").fillna(
        1
    )
    s_df["배송메모"] = s_df.get("배송메세지", "")
    s_df["주문번호"] = s_df.get("주문번호", "")
    frames.append(s_df)

  # 올웨이즈 데이터 표준화 (옵션명에서 상품명 추출)
  if always_df is not None and not always_df.empty:
    a_df = always_df.copy()
    a_df["수령자이름"] = a_df.get("수령인", "")
    a_df["수령자전화"] = a_df.get("수령인 연락처", "")
    a_df["수령자휴대폰"] = a_df.get("수령인 연락처", "")
    a_df["수령자우편번호"] = a_df.get("우편번호", "")
    a_df["수령자주소"] = a_df.get("주소", "")
    a_df["상품명_원본"] = a_df.get("상품명", "")
    a_df["옵션_원본"] = a_df.get("옵션", "")
    a_df["상품수량"] = pd.to_numeric(a_df.get("수량", 1), errors="coerce").fillna(
        1
    )
    a_df["배송메모"] = ""
    a_df["주문번호"] = a_df.get("주문아이디", "")
    frames.append(a_df)

  if not frames:
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

  combined = pd.concat(frames, ignore_index=True)

  garam_rows = []
  kistic_rows = []
  frozen_rows = []

  for _, row in combined.iterrows():
    p_name = str(row["상품명_원본"])
    opt_name = str(row["옵션_원본"])
    qty = int(row["상품수량"])

    # 1. 가람식품 (부산어묵바류)
    if "어묵바" in p_name or "어묵바" in opt_name:
      target_name = "오리지날 부산어묵바"
      if "매콤달콤" in opt_name or "매콤달콤" in p_name:
        target_name = "매콤달콤 부산어묵바"
      elif "오징어야채" in opt_name or "오징어야채" in p_name:
        target_name = "오징어야채 부산어묵바"
      elif "체다치즈" in opt_name or "체다치즈" in p_name:
        target_name = "체다치즈 부산어묵바"

      # 합배송 불가: 수량만큼 행 분리 및 수령자명 뒤 숫자 부여
      for i in range(qty):
        new_row = row.copy()
        if qty > 1:
          new_row["수령자이름"] = f"{row['수령자이름']}{i+1}"
        new_row["상품명"] = target_name
        new_row["상품수량"] = 1
        garam_rows.append(new_row)

    # 2. 키스틱류
    elif "키스틱" in p_name or "키스틱" in opt_name:
      is_40 = "40개" in p_name or "40개" in opt_name

      if is_40:
        if qty == 2:
          # 40개 2개 구매 -> 100개 1세트로 변환
          new_row = row.copy()
          new_row["상품명"] = "키스틱 15g x 100개"
          new_row["상품수량"] = 1
          kistic_rows.append(new_row)
        elif qty == 3:
          # 홀수 3개 구매 -> 40개 1세트 + 100개 1세트로 분할
          row1 = row.copy()
          row1["상품명"] = "키스틱 15g x 40개"
          row1["상품수량"] = 1
          kistic_rows.append(row1)

          row2 = row.copy()
          row2["수령자이름"] = f"{row['수령자이름']}2"
          row2["상품명"] = "키스틱 15g x 100개"
          row2["상품수량"] = 1
          kistic_rows.append(row2)
        else:
          new_row = row.copy()
          new_row["상품명"] = "키스틱 15g x 40개"
          new_row["상품수량"] = qty
          kistic_rows.append(new_row)
      else:
        new_row = row.copy()
        new_row["상품명"] = "키스틱 15g x 100개"
        new_row["상품수량"] = qty
        kistic_rows.append(new_row)

    # 3. 냉동식품류 (군만두, 김말이)
    elif "만두" in p_name or "고추잡채" in p_name:
      new_row = row.copy()
      new_row["상품명"] = "더 바삭한 중화 고추잡채 군만두 1.2kg"
      new_row["상품수량"] = qty
      frozen_rows.append(new_row)

    elif "김말이" in p_name:
      new_row = row.copy()
      new_row["상품명"] = "김말이튀김400g"
      new_row["상품수량"] = qty * 3  # 기본 1세트당 3팩 곱하기
      frozen_rows.append(new_row)

  garam_df = pd.DataFrame(garam_rows) if garam_rows else pd.DataFrame()
  kistic_df = pd.DataFrame(kistic_rows) if kistic_rows else pd.DataFrame()
  frozen_df = pd.DataFrame(frozen_rows) if frozen_rows else pd.DataFrame()

  return garam_df, kistic_df, frozen_df


# 2. 실행 버튼 및 압축 다운로드 섹션
st.subheader("2. 맞춤형 발주서 변환 실행")

if st.button("🚀 발주서 변환 및 압축파일 생성하기", type="primary"):
  if shopmoa_file is None and always_file is None:
    st.warning("최소 한 개 이상의 발주서 파일을 업로드해 주세요.")
  else:
    try:
      s_df = pd.read_excel(shopmoa_file) if shopmoa_file else None
      a_df = pd.read_excel(always_file) if always_file else None

      garam_df, kistic_df, frozen_df = process_custom_orders(s_df, a_df)

      # 메모리에 ZIP 파일 생성
      zip_buffer = io.BytesIO()
      with zipfile.ZipFile(
          zip_buffer, "w", zipfile.ZIP_DEFLATED
      ) as zip_file:
        if not garam_df.empty:
          g_io = io.BytesIO()
          with pd.ExcelWriter(g_io, engine="openpyxl") as writer:
            garam_df.to_excel(writer, index=False)
          zip_file.writestr("가람식품_발주서.xlsx", g_io.getvalue())

        if not kistic_df.empty:
          k_io = io.BytesIO()
          with pd.ExcelWriter(k_io, engine="openpyxl") as writer:
            kistic_df.to_excel(writer, index=False)
          zip_file.writestr("키스틱_발주서.xlsx", k_io.getvalue())

        if not frozen_df.empty:
          f_io = io.BytesIO()
          with pd.ExcelWriter(f_io, engine="openpyxl") as writer:
            frozen_df.to_excel(writer, index=False)
          zip_file.writestr("냉동식품_발주서.xlsx", f_io.getvalue())

      zip_buffer.seek(0)

      st.success(
          "✨ 발주서 변환이 완료되었습니다! 아래 버튼을 눌러 통합 압축파일을"
          " 다운로드하세요."
      )

      st.download_button(
          label="📥 3개 공급처 발주서 ZIP 압축파일 다운로드",
          data=zip_buffer,
          file_name="마켓지니_통합발주서.zip",
          mime="application/zip",
      )

    except Exception as e:
      st.error(f"파일 처리 중 오류가 발생했습니다: {e}")
