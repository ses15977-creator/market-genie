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
    "샵모아와 올웨이즈 발주서 파일을 업로드한 후 실행 버튼을 누르면, 지정된 양식에 맞춘 3개 공급처별 발주서 파일이 담긴 ZIP 압축파일을 생성합니다."
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

  # 현재 날짜 스트링 생성 (YYYYMMDD 형식, 가람발주서용)
  date_str = datetime.now().strftime("%Y%m%d")

  # 샵모아 데이터 표준화
  if shopmoa_df is not None and not shopmoa_df.empty:
    s_df = shopmoa_df.copy()
    s_df["원격_받는분성명"] = s_df.get("수취인명", "")
    s_df["원격_받는분전화번호"] = s_df.get("수취인 전화번호", "")
    s_df["원격_받는분기타연락처"] = s_df.get("수취인 핸드폰번호", "")
    s_df["원격_받는분우편번호"] = s_df.get("우편번호", "")
    s_df["원격_받는분주소"] = s_df.get("수취인주소", "")
    s_df["상품명_원본"] = s_df.get("상품명", "")
    s_df["옵션_원본"] = s_df.get("옵션", "")
    s_df["상품수량"] = pd.to_numeric(s_df.get("수량", 1), errors="coerce").fillna(
        1
    )
    s_df["배송메세지1"] = s_df.get("배송메세지", "")
    s_df["주문번호"] = s_df.get("주문번호", "")
    s_df["주문일"] = date_str
    s_df["판매처"] = s_df.get("사이트", "샵모아")
    frames.append(s_df)

  # 올웨이즈 데이터 표준화
  if always_df is not None and not always_df.empty:
    a_df = always_df.copy()
    a_df["원격_받는분성명"] = a_df.get("수령인", "")
    a_df["원격_받는분전화번호"] = a_df.get("수령인 연락처", "")
    a_df["원격_받는분기타연락처"] = a_df.get("수령인 연락처", "")
    a_df["원격_받는분우편번호"] = a_df.get("우편번호", "")
    a_df["원격_받는분주소"] = a_df.get("주소", "")
    a_df["상품명_원본"] = a_df.get("상품명", "")
    a_df["옵션_원본"] = a_df.get("옵션", "")
    a_df["상품수량"] = pd.to_numeric(a_df.get("수량", 1), errors="coerce").fillna(
        1
    )
    a_df["배송메세지1"] = ""
    a_df["주문번호"] = a_df.get("주문아이디", "")
    a_df["주문일"] = date_str
    a_df["판매처"] = "올웨이즈"
    frames.append(a_df)

  if not frames:
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), date_str

  combined = pd.concat(frames, ignore_index=True)

  garam_rows = []
  kistic_rows = []
  frozen_rows = []

  for _, row in combined.iterrows():
    p_name = str(row["상품명_원본"])
    opt_name = str(row["옵션_원본"])
    qty = int(row["상품수량"])

    # 1. 가람식품 양식 생성 함수 (거래처코드 16 고정)
    def create_garam_row(name, quantity):
      return {
          "받는분성명": name,
          "받는분전화번호": row["원격_받는분전화번호"],
          "받는분기타연락처": row["원격_받는분기타연락처"],
          "받는분우편번호": row["원격_받는분우편번호"],
          "받는분주소": row["원격_받는분주소"],
          "내품수량": quantity,
          "배송메세지1": row["배송메세지1"],
          "출력일": "",
          "운임구분": "",
          "기본운임": "",
          "고객사용번호": "",
          "품명": "",
          "판매처": row["판매처"],
          "주문번호": row["주문번호"],
          "주문일": row["주문일"],
          "판매가": "",
          "정산금액": "",
          "거래처코드": 16,
      }

    # 2. 키스틱 / 냉동식품 양식 생성 함수 (빨간색 컬럼만 채우고 배송메모, 판매처, 발주일 등은 비워둠)
    def create_standard_row(name, quantity):
      return {
          "수령자이름": name,
          "수령자전화": row["원격_받는분전화번호"],
          "수령자휴대폰": row["원격_받는분기타연락처"],
          "수령자우편번호": row["원격_받는분우편번호"],
          "수령자주소": row["원격_받는분주소"],
          "상품수량": quantity,
          "배송메모": "",  # 비워둠
          "제조사": "",
          "카테고리": "",
          "품절": "",
          "배송 보류": "",
          "상품명": "",
          "판매처": "",  # 비워둠
          "주문번호": row["주문번호"],
          "발주일": "",  # 비워둠
          "관리번호": "",
          "상태": "",
          "송장번호": "",
      }

    # 1. 가람식품 (부산어묵바류) 분류
    if "어묵바" in p_name or "어묵바" in opt_name:
      target_name = "오리지날 부산어묵바 80g x 10개"
      if "매콤달콤" in opt_name or "매콤달콤" in p_name:
        target_name = "매콤달콤 부산어묵바 80g x 10개"
      elif "오징어야채" in opt_name or "오징어야채" in p_name:
        target_name = "오징어야채 부산어묵바 80g x 10개"
      elif "체다치즈" in opt_name or "체다치즈" in p_name:
        target_name = "체다치즈 부산어묵바 80g x 10개"

      base_name = str(row["원격_받는분성명"])
      for i in range(qty):
        r_name = f"{base_name}{i+1}" if qty > 1 else base_name
        r_copy = create_garam_row(r_name, 1)
        r_copy["품명"] = target_name
        garam_rows.append(r_copy)

    # 2. 키스틱류 분류
    elif "키스틱" in p_name or "키스틱" in opt_name:
      is_40 = "40개" in p_name or "40개" in opt_name
      base_name = str(row["원격_받는분성명"])

      if is_40:
        if qty == 2:
          r_copy = create_standard_row(base_name, 1)
          r_copy["상품명"] = "키스틱 15g x 100개"
          kistic_rows.append(r_copy)
        elif qty == 3:
          r1 = create_standard_row(base_name, 1)
          r1["상품명"] = "키스틱 15g x 40개"
          kistic_rows.append(r1)

          r2 = create_standard_row(f"{base_name}2", 1)
          r2["상품명"] = "키스틱 15g x 100개"
          kistic_rows.append(r2)
        else:
          r_copy = create_standard_row(base_name, qty)
          r_copy["상품명"] = "키스틱 15g x 40개"
          kistic_rows.append(r_copy)
      else:
        r_copy = create_standard_row(base_name, qty)
        r_copy["상품명"] = "키스틱 15g x 100개"
        kistic_rows.append(r_copy)

    # 3. 냉동식품류 (군만두, 김말이) 분류
    elif "만두" in p_name or "고추잡채" in p_name:
      base_name = str(row["원격_받는분성명"])
      r_copy = create_standard_row(base_name, qty)
      r_copy["상품명"] = "더 바삭한 중화 고추잡채 군만두 1.2kg"
      frozen_rows.append(r_copy)

    elif "김말이" in p_name:
      base_name = str(row["원격_받는분성명"])
      r_copy = create_standard_row(base_name, qty * 3)
      r_copy["상품명"] = "김말이튀김400g"
      frozen_rows.append(r_copy)

  # 컬럼 정의
  garam_cols = [
      "받는분성명",
      "받는분전화번호",
      "받는분기타연락처",
      "받는분우편번호",
      "받는분주소",
      "내품수량",
      "배송메세지1",
      "출력일",
      "운임구분",
      "기본운임",
      "고객사용번호",
      "품명",
      "판매처",
      "주문번호",
      "주문일",
      "판매가",
      "정산금액",
      "거래처코드",
  ]

  kistic_cols = [
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
      pd.DataFrame(kistic_rows)[kistic_cols]
      if kistic_rows
      else pd.DataFrame(columns=kistic_cols)
  )
  frozen_df = (
      pd.DataFrame(frozen_rows)[kistic_cols]
      if frozen_rows
      else pd.DataFrame(columns=kistic_cols)
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
