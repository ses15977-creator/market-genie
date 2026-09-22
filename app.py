from datetime import datetime
import io
import zipfile
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="마켓지니 판매관리 프로그램", page_icon="📦", layout="centered"
)

# 세션 상태 초기화 (누적 데이터 저장용)
if "accumulated_sales" not in st.session_state:
  st.session_state["accumulated_sales"] = pd.DataFrame()
if "accumulated_garam" not in st.session_state:
  st.session_state["accumulated_garam"] = pd.DataFrame()
if "accumulated_kistic" not in st.session_state:
  st.session_state["accumulated_kistic"] = pd.DataFrame()
if "accumulated_frozen" not in st.session_state:
  st.session_state["accumulated_frozen"] = pd.DataFrame()

st.title("📦 마켓지니 판매관리 프로그램")
st.write(
    "발주서 파일을 업로드하면, 플랫폼별 수수료율에 따른 매출 및 순수익을 분석하고"
    " 공급처별 통합 발주서를 생성합니다."
)

st.markdown("---")

# 0. 플랫폼별 수수료율 설정 사이드바 또는 상단 설정 영역
st.subheader("⚙️ 플랫폼 수수료율 설정 (%)")
col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
with col_f1:
  fee_smart = st.number_input("스마트스토어", value=5.80, step=0.1, format="%.2f")
with col_f2:
  fee_always = st.number_input("올웨이즈", value=5.50, step=0.1, format="%.2f")
with col_f3:
  fee_coupang = st.number_input("쿠팡", value=10.80, step=0.1, format="%.2f")
with col_f4:
  fee_gmarket = st.number_input("지마켓", value=13.00, step=0.1, format="%.2f")
with col_f5:
  fee_auction = st.number_input("옥션", value=13.00, step=0.1, format="%.2f")

fee_rates = {
    "스마트스토어": fee_smart / 100.0,
    "네이버": fee_smart / 100.0,
    "올웨이즈": fee_always / 100.0,
    "쿠팡": fee_coupang / 100.0,
    "지마켓": fee_gmarket / 100.0,
    "G마켓": fee_gmarket / 100.0,
    "옥션": fee_auction / 100.0,
}

st.markdown("---")

# 1. 파일 업로드 섹션
st.subheader("1. 발주서 파일 업로드")
col1, col2 = st.columns(2)

with col1:
  shopmoa_file = st.file_uploader(
      "샵모아 / 통합 발주서 파일 (.xlsx)", type=["xlsx", "xls"], key="shopmoa"
  )

with col2:
  always_file = st.file_uploader(
      "올웨이즈 발주서 파일 (.xlsx)", type=["xlsx", "xls"], key="always"
  )


def detect_platform(row, default_channel):
  """업로드된 데이터 내에서 판매처(플랫폼) 명칭을 감지합니다."""
  # 컬럼 탐색
  for col in row.index:
    val_str = str(row[col])
    for p_name in ["쿠팡", "스마트스토어", "네이버", "지마켓", "G마켓", "옥션", "올웨이즈"]:
      if p_name in val_str or p_name in str(col):
        if "네이버" in p_name:
          return "스마트스토어"
        if "G마켓" in p_name:
          return "지마켓"
        return p_name
  return default_channel


def calculate_item_finance(product_name, option_name, channel):
  """상품별 원가, 배송비, 판매가 계산 및 플랫폼 수수료 적용"""
  p_str = str(product_name)
  o_str = str(option_name)
  combined_text = p_str + " " + o_str

  selling_price = 0
  cost_price = 0
  shipping_fee = 0
  item_category = "기타"

  # 1. 키스틱
  if "키스틱" in combined_text:
    shipping_fee = 2900
    if "40개" in combined_text:
      selling_price = 9900
      cost_price = 113 * 40
      item_category = "키스틱 40개입"
    else:
      selling_price = 19900
      cost_price = 113 * 100
      item_category = "키스틱 100개입"

  # 2. 고추잡채만두
  elif "만두" in combined_text or "고추잡채" in combined_text:
    shipping_fee = 3900
    selling_price = 13900
    cost_price = 4700
    item_category = "고추잡채군만두 1.2kg"

  # 3. 김말이튀김
  elif "김말이" in combined_text:
    shipping_fee = 3900
    selling_price = 13900
    cost_price = 1700 * 3
    item_category = "김말이튀김 400g (3개 세트)"

  # 4. 부산어묵바
  elif "어묵바" in combined_text:
    shipping_fee = 4300
    if "매콤달콤" in combined_text:
      selling_price = 19900
      cost_price = int(560 * 1.1 * 10)
      item_category = "매콤달콤 부산어묵바"
    elif "오징어야채" in combined_text:
      selling_price = 20900
      cost_price = int(575 * 1.1 * 10)
      item_category = "오징어야채 부산어묵바"
    elif "체다치즈" in combined_text:
      selling_price = 21900
      cost_price = int(646 * 1.1 * 10)
      item_category = "체다치즈 부산어묵바"
    else:
      selling_price = 18900
      cost_price = int(536 * 1.1 * 10)
      item_category = "오리지날 부산어묵바"
  else:
    selling_price = 10000
    cost_price = 5000
    shipping_fee = 3000
    item_category = "기타상품"

  # 선택된 플랫폼별 수수료율 적용
  rate = fee_rates.get(channel, 0.10)
  platform_fee = selling_price * rate
  net_profit = selling_price - cost_price - shipping_fee - platform_fee

  return {
      "카테고리": item_category,
      "판매가": selling_price,
      "원가": cost_price,
      "배송비": shipping_fee,
      "플랫폼수수료": platform_fee,
      "순수익": net_profit,
  }


def process_custom_orders(shopmoa_df, always_df):
  frames = []
  sales_data_list = []
  date_str = datetime.now().strftime("%Y-%m-%d")

  def parse_dataframe(df, default_channel_name):
    if df is None or df.empty:
      return
    for _, row in df.iterrows():
      # 파일 내부에서 실제 판매처 컬럼 확인 시도
      detected_channel = default_channel_name
      for col in ["판매처", "쇼핑몰", "채널", "사이트"]:
        if col in row and pd.notna(row[col]):
          val = str(row[col])
          if "쿠팡" in val:
            detected_channel = "쿠팡"
          elif "스마트스토어" in val or "네이버" in val:
            detected_channel = "스마트스토어"
          elif "지마켓" in val or "G마켓" in val:
            detected_channel = "지마켓"
          elif "옥션" in val:
            detected_channel = "옥션"
          elif "올웨이즈" in val:
            detected_channel = "올웨이즈"

      if default_channel_name == "샵모아":
        sname = row.get("수취인명", "")
        phone = row.get("수취인 전화번호", "")
        mobile = row.get("수취인 핸드폰번호", "")
        zipcode = row.get("우편번호", "")
        address = row.get("수취인주소", "")
        p_name = row.get("상품명", "")
        opt_name = row.get("옵션", "")
        qty = int(pd.to_numeric(row.get("수량", 1), errors="coerce"))
        msg = row.get("배송메세지", "")
        order_id = row.get("주문번호", "")
      else:
        sname = row.get("수령인", "")
        phone = row.get("수령인 연락처", "")
        mobile = row.get("수령인 연락처", "")
        zipcode = row.get("우편번호", "")
        address = row.get("주소", "")
        p_name = row.get("상품명", "")
        opt_name = row.get("옵션", "")
        qty = int(pd.to_numeric(row.get("수량", 1), errors="coerce"))
        msg = ""
        order_id = row.get("주문아이디", "")

      fin = calculate_item_finance(p_name, opt_name, detected_channel)

      for _ in range(max(1, qty)):
        sales_data_list.append({
            "업로드일자": date_str,
            "판매처": detected_channel,
            "주문번호": str(order_id),
            "상품명": fin["카테고리"],
            "판매가": fin["판매가"],
            "원가": fin["원가"],
            "배송비": fin["배송비"],
            "플랫폼수수료": fin["플랫폼수수료"],
            "순수익": fin["순수익"],
        })

      base_row = {
          "원격_받는분성명": sname,
          "원격_받는분전화번호": phone,
          "원격_받는분기타연락처": mobile,
          "원격_받는분우편번호": zipcode,
          "원격_받는분주소": address,
          "상품명_원본": p_name,
          "옵션_원본": opt_name,
          "상품수량": qty,
          "배송메세지1": msg,
          "주문번호": order_id,
          "주문일": date_str,
          "판매처": detected_channel,
      }
      frames.append(base_row)

  parse_dataframe(shopmoa_df, "샵모아")
  parse_dataframe(always_df, "올웨이즈")

  if not frames:
    return (
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        date_str,
    )

  combined = pd.DataFrame(frames)
  sales_df = pd.DataFrame(sales_data_list)

  garam_rows = []
  kistic_rows = []
  frozen_rows = []

  for _, row in combined.iterrows():
    p_name = str(row["상품명_원본"])
    opt_name = str(row["옵션_원본"])
    qty = int(row["상품수량"])

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

    def create_standard_row(name, quantity):
      return {
          "수령자이름": name,
          "수령자전화": row["원격_받는분전화번호"],
          "수령자휴대폰": row["원격_받는분기타연락처"],
          "수령자우편번호": row["원격_받는분우편번호"],
          "수령자주소": row["원격_받는분주소"],
          "상품수량": quantity,
          "배송메모": "",
          "제조사": "",
          "카테고리": "",
          "품절": "",
          "배송 보류": "",
          "상품명": "",
          "판매처": row["판매처"],
          "주문번호": row["주문번호"],
          "발주일": "",
          "관리번호": "",
          "상태": "",
          "송장번호": "",
      }

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

  return garam_df, kistic_df, frozen_df, sales_df, date_str


# 2. 실행 버튼 및 압축 다운로드 섹션
st.markdown("---")
st.subheader("2. 맞춤형 발주서 변환 및 누적 수익 분석 실행")

col_btn1, col_btn2 = st.columns([3, 1])
with col_btn1:
  run_clicked = st.button(
      "🚀 발주서 변환 및 누적 데이터 반영하기", type="primary"
  )
with col_btn2:
  if st.button("🧹 누적 데이터 초기화"):
    st.session_state["accumulated_sales"] = pd.DataFrame()
    st.session_state["accumulated_garam"] = pd.DataFrame()
    st.session_state["accumulated_kistic"] = pd.DataFrame()
    st.session_state["accumulated_frozen"] = pd.DataFrame()
    st.success("누적 데이터가 초기화되었습니다.")
    st.rerun()

if run_clicked:
  if shopmoa_file is None and always_file is None:
    st.warning("최소 한 개 이상의 발주서 파일을 업로드해 주세요.")
  else:
    try:
      s_df = pd.read_excel(shopmoa_file) if shopmoa_file else None
      a_df = pd.read_excel(always_file) if always_file else None

      garam_df, kistic_df, frozen_df, sales_df, date_str = (
          process_custom_orders(s_df, a_df)
      )

      if not sales_df.empty:
        st.session_state["accumulated_sales"] = pd.concat(
            [st.session_state["accumulated_sales"], sales_df], ignore_index=True
        )
      if not garam_df.empty:
        st.session_state["accumulated_garam"] = pd.concat(
            [st.session_state["accumulated_garam"], garam_df], ignore_index=True
        )
      if not kistic_df.empty:
        st.session_state["accumulated_kistic"] = pd.concat(
            [st.session_state["accumulated_kistic"], kistic_df], ignore_index=True
        )
      if not frozen_df.empty:
        st.session_state["accumulated_frozen"] = pd.concat(
            [st.session_state["accumulated_frozen"], frozen_df], ignore_index=True
        )

      st.success(
          f"✨ 새로운 데이터가 성공적으로 누적 반영되었습니다! (기준일자: {date_str})"
      )

    except Exception as e:
      st.error(f"파일 처리 중 오류가 발생했습니다: {e}")

# --- [플랫폼별 누적 매출 및 순수익 현황 대시보드] ---
st.markdown("---")
st.subheader("📊 [누적 데이터] 플랫폼별 매출 및 순수익 현황")

acc_sales = st.session_state["accumulated_sales"]

if not acc_sales.empty:
  total_orders = len(acc_sales)
  total_revenue = acc_sales["판매가"].sum()
  total_cost = acc_sales["원가"].sum()
  total_shipping = acc_sales["배송비"].sum()
  total_platform_fee = acc_sales["플랫폼수수료"].sum()
  total_net_profit = acc_sales["순수익"].sum()

  m1, m2, m3, m4 = st.columns(4)
  m1.metric("누적 총 주문 건수", f"{total_orders:,} 건")
  m2.metric("누적 총 판매 매출액", f"{total_revenue:,.0f} 원")
  m3.metric(
      "누적 원가+배송+수수료",
      f"{(total_cost + total_shipping + total_platform_fee):,.0f} 원",
  )
  m4.metric(
      "누적 총 순수익",
      f"{total_net_profit:,.0f} 원",
      delta=(
          f"마진율 {(total_net_profit/total_revenue*100):.1f}%"
          if total_revenue > 0
          else "0%"
      ),
  )

  st.markdown("##### 🛒 플랫폼별 누적 매출 및 순수익 상세")
  platform_summary = (
      acc_sales.groupby("판매처")
      .agg(
          주문건수=("판매가", "count"),
          총판매가=("판매가", "sum"),
          총원가=("원가", "sum"),
          총배송비=("배송비", "sum"),
          플랫폼수수료합계=("플랫폼수수료", "sum"),
          총순수익=("순수익", "sum"),
      )
      .reset_index()
  )
  st.dataframe(platform_summary, use_container_width=True)

  st.markdown("##### 📅 업로드 일자별 누적 요약")
  date_summary = (
      acc_sales.groupby("업로드일자")
      .agg(
          주문건수=("판매가", "count"),
          매출액=("판매가", "sum"),
          순수익=("순수익", "sum"),
      )
      .reset_index()
  )
  st.dataframe(date_summary, use_container_width=True)

  zip_buffer = io.BytesIO()
  with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
    if not st.session_state["accumulated_garam"].empty:
      g_io = io.BytesIO()
      with pd.ExcelWriter(g_io, engine="openpyxl") as writer:
        st.session_state["accumulated_garam"].to_excel(writer, index=False)
      zip_file.writestr("가람식품_통합누적_발주서.xlsx", g_io.getvalue())

    if not st.session_state["accumulated_kistic"].empty:
      k_io = io.BytesIO()
      with pd.ExcelWriter(k_io, engine="openpyxl") as writer:
        st.session_state["accumulated_kistic"].to_excel(writer, index=False)
      zip_file.writestr("키스틱_통합누적_발주서.xlsx", k_io.getvalue())

    if not st.session_state["accumulated_frozen"].empty:
      f_io = io.BytesIO()
      with pd.ExcelWriter(f_io, engine="openpyxl") as writer:
        st.session_state["accumulated_frozen"].to_excel(writer, index=False)
      zip_file.writestr("냉동식품_통합누적_발주서.xlsx", f_io.getvalue())

  zip_buffer.seek(0)

  st.markdown("---")
  st.download_button(
      label="📥 전체 누적 통합 발주서 ZIP 압축파일 다운로드",
      data=zip_buffer,
      file_name="마켓지니_전체누적_통합발주서.zip",
      mime="application/zip",
  )
else:
  st.info(
      "아직 업로드 및 반영된 매출 데이터가 없습니다. 파일을 업로드하고 버튼을"
      " 눌러주세요."
  )
