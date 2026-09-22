from datetime import datetime
import io
import zipfile
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="마켓지니 스마트 발주서 변환기", page_icon="📦", layout="centered"
)

st.title("📦 마켓지니 스마트 발주서 변환기")
st.write(
    "샵모아와 올웨이즈 발주서 파일을 업로드한 후 실행 버튼을 누르면, 날짜가 반영된 3개 공급처별 양식 파일이 담긴 ZIP 압축파일을 생성합니다."
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

  # 현재 날짜 스트링 생성 (YYYYMMDD 형식, 예: 20260921)
  date_str = datetime.now().strftime("%Y%m%d")

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
    s_df["발주일"] = date_str
    frames.append(s_df)

  # 올웨이즈 데이터 표준화
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
    a_df["발주일"] = date_str
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

    # 공통 기본 양식 필드 구성
    base_dict = {
        "수령자이름": row["수령자이름"],
        "수령자전화": row["수령자전화"],
        "수령자휴대폰": row["수령자휴대폰"],
        "수령자우편번호": row["수령자우편번호"],
        "수령자주소": row["수령자주소"],
        "배송메모": row["배송메모"],
        "제조사": "",
        "카테고리": "",
        "품절": "",
        "배송 보류": "",
        "판매처": "",
        "주문번호": row["주문번호"],
        "발주일": row["발주일"],
        "관리번호": "",
        "상태": "",
        "송장번호": "",
    }

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
        r_copy = base_dict.copy()
        if qty > 1:
          r_copy["수령자이름"] = f"{row['수령자이름']}{i+1}"
        r_copy["상품명"] = target_name
        r_copy["상품수량"] = 1
        r_copy[1] = 1  # 가람 양식 특유의 수량 필드 호환
        garam_rows.append(r_copy)

    # 2. 키스틱류
    elif "키스틱" in p_name or "키스틱" in opt_name:
      is_40 = "40개" in p_name or "40개" in opt_name

      if is_40:
        if qty == 2:
          r_copy = base_dict.copy()
          r_copy["상품명"] = "키스틱 15g x 100개"
          r_copy["상품수량"] = 1
          r_copy[1] = 1
          kistic_rows.append(r_copy)
        elif qty == 3:
          r1 = base_dict.copy()
          r1["상품명"] = "키스틱 15g x 40개"
          r1["상품수량"] = 1
          r1[1] = 1
          kistic_rows.append(r1)

          r2 = base_dict.copy()
          r2["수령자이름"] = f"{row['수령자이름']}2"
          r2["상품명"] = "키스틱 15g x 100개"
          r2["상품수량"] = 1
          r2[1] = 1
          kistic_rows.append(r2)
        else:
          r_copy = base_dict.copy()
          r_copy["상품명"] = "키스틱 15g x 40개"
          r_copy["상품수량"] = qty
          r_copy[1] = qty
          kistic_rows.append(r_copy)
      else:
        r_copy = base_dict.copy()
        r_copy["상품명"] = "키스틱 15g x 100개"
        r_copy["상품수량"] = qty
        r_copy[1] = qty
        kistic_rows.append(r_copy)

    # 3. 냉동식품류 (군만두, 김말이)
    elif "만두" in p_name or "고추잡채" in p_name:
      r_copy = base_dict.copy()
      r_copy["상품명"] = "더 바삭한 중화 고추잡채 군만두 1.2kg"
      r_copy["상품수량"] = qty
      frozen_rows.append(r_copy)

    elif "김말이" in p_name:
      r_copy = base_dict.copy()
      r_copy["상품명"] = "김말이튀김400g"
      r_copy["상품수량"] = qty * 3
      frozen_rows.append(r_copy)

  # 최종 데이터프레임 변환 (요청하신 정확한 컬럼 순서 및 양식 유지)
  garam_cols = [
      "수령자이름",
      "수령자전화",
      "수령자휴대폰",
      "수령자우편번호",
      "수령자주소",
      1,
      "배송메모",
      "제조사",
      "카테고리",
      "품절",
      "배송 보류",
      "상품명",
      "판매처",
      "주문번호",
      "발주일",
      "관리번호",
      "상태",
      "송장번호",
  ]
  standard_cols = [
      "수령자이름",
      "수령자전화",
      "수령자휴대폰",
      "수령자우편번호",
      "수령자주소",
      "상품수량",
      "배송메모",
      "제조사",
      "카테고리",
      "품절",
      "배송 보류",
      "상품명",
      "판매처",
      "주문번호",
      "발주일",
      "관리번호",
      "상태",
      "송장번호",
  ]

  garam_df = (
      pd.DataFrame(garam_rows)[garam_cols]
      if garam_rows
      else pd.DataFrame(columns=garam_cols)
  )
  kistic_df = (
      pd.DataFrame(kistic_rows)[garam_cols]
      if kistic_rows
      else pd.DataFrame(columns=garam_cols)
  )
  frozen_df = (
      pd.DataFrame(frozen_rows)[standard_cols]
      if frozen_rows
      else pd.DataFrame(columns=standard_cols)
  )

  return garam_df, kistic_df, frozen_df, date_str


# 2. 실행 버튼 및 압축 다운로드 섹션
st.subheader("2. 맞춤형 발주서 변환 실행")

if st.button("🚀 발주서 변환 및 압축파일 생성하기", type="primary"):
  if shopmoa_file is None and always_file is None:
    st.warning("최소 한 개 이상의 발주서 파일을 업로드해 주세요.")
  else:
    try:
      s_df = pd.read_excel(shopmoa_file) if shopmoa_file else None
      a_df = pd.read_excel(always_file) if always_file else None

      garam_df, kistic_df, frozen_df, date_str = process_custom_orders(
          s_df, a_df
      )

      # 메모리에 ZIP 파일 생성 (파일명에 발주일자 반영)
      zip_buffer = io.BytesIO()
      with zipfile.ZipFile(
          zip_buffer, "w", zipfile.ZIP_DEFLATED
      ) as zip_file:
        if not garam_df.empty:
          g_io = io.BytesIO()
          with pd.ExcelWriter(g_io, engine="openpyxl") as writer:
            garam_df.to_excel(writer, index=False)
          zip_file.writestr(f"가람식품_발주서_{date_str}.xlsx", g_io.getvalue())

        if not kistic_df.empty:
          k_io = io.BytesIO()
          with pd.ExcelWriter(k_io, engine="openpyxl") as writer:
            kistic_df.to_excel(writer, index=False)
          zip_file.writestr(f"키스틱_발주서_{date_str}.xlsx", k_io.getvalue())

        if not frozen_df.empty:
          f_io = io.BytesIO()
          with pd.ExcelWriter(f_io, engine="openpyxl") as writer:
            frozen_df.to_excel(writer, index=False)
          zip_file.writestr(f"냉동식품_발주서_{date_str}.xlsx", f_io.getvalue())

      zip_buffer.seek(0)

      st.success(
          f"✨ [{date_str}] 기준 발주서 변환이 완료되었습니다! 아래 버튼을 눌러"
          " 통합 압축파일을 다운로드하세요."
      )

      st.download_button(
          label=f"📥 3개 공급처 발주서 ZIP 압축파일 다운로드 ({date_str})",
          data=zip_buffer,
          file_name=f"마켓지니_통합발주서_{date_str}.zip",
          mime="application/zip",
      )

    except Exception as e:
      st.error(f"파일 처리 중 오류가 발생했습니다: {e}")
