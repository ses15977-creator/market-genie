from datetime import datetime
import io
import zipfile
import pandas as pd
import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="마켓지니 통합 판매관리 프로그램", page_icon="📦", layout="centered"
)

# 1. 세션 상태 초기화 (누적 데이터 및 재고/상품 마스터 관리)
if "accumulated_sales" not in st.session_state:
  st.session_state["accumulated_sales"] = pd.DataFrame()
if "accumulated_garam" not in st.session_state:
  st.session_state["accumulated_garam"] = pd.DataFrame()
if "accumulated_kistic" not in st.session_state:
  st.session_state["accumulated_kistic"] = pd.DataFrame()
if "accumulated_frozen" not in st.session_state:
  st.session_state["accumulated_frozen"] = pd.DataFrame()

# 초기 재고 설정
if "inventory" not in st.session_state:
  st.session_state["inventory"] = {
      "키스틱 15g x 40개": 500,
      "키스틱 15g x 100개": 500,
      "더 바삭한 중화 고추잡채 군만두 1.2kg": 300,
      "김말이튀김400g": 400,
      "오리지날 부산어묵바 80g x 10개": 300,
      "매콤달콤 부산어묵바 80g x 10개": 300,
      "오징어야채 부산어묵바 80g x 10개": 300,
      "체다치즈 부산어묵바 80g x 10개": 300,
  }

# 🛠️ 상품 마스터 관리 (판매가, 원가, 배송비, 부가세별도 여부 설정)
if "product_master" not in st.session_state:
  st.session_state["product_master"] = {
      "키스틱 15g x 40개": {
          "selling_price": 9900,
          "cost_price": 113 * 40,
          "shipping_fee": 2900,
          "vat_separate": False,
      },
      "키스틱 15g x 100개": {
          "selling_price": 19900,
          "cost_price": 113 * 100,
          "shipping_fee": 2900,
          "vat_separate": False,
      },
      "더 바삭한 중화 고추잡채 군만두 1.2kg": {
          "selling_price": 13900,
          "cost_price": 4700,
          "shipping_fee": 3900,
          "vat_separate": False,
      },
      "김말이튀김400g": {
          "selling_price": 13900,
          "cost_price": 1700 * 3,
          "shipping_fee": 3900,
          "vat_separate": False,
      },
      "오리지날 부산어묵바 80g x 10개": {
          "selling_price": 18900,
          "cost_price": int(536 * 1.1 * 10),
          "shipping_fee": 4300,
          "vat_separate": True,
      },
      "매콤달콤 부산어묵바 80g x 10개": {
          "selling_price": 19900,
          "cost_price": int(560 * 1.1 * 10),
          "shipping_fee": 4300,
          "vat_separate": True,
      },
      "오징어야채 부산어묵바 80g x 10개": {
          "selling_price": 20900,
          "cost_price": int(575 * 1.1 * 10),
          "shipping_fee": 4300,
          "vat_separate": True,
      },
      "체다치즈 부산어묵바 80g x 10개": {
          "selling_price": 21900,
          "cost_price": int(646 * 1.1 * 10),
          "shipping_fee": 4300,
          "vat_separate": True,
      },
  }

st.title("📦 마켓지니 판매 및 재고 관리 프로그램")
st.write(
    "발주서 업로드 시 파일 내 날짜 기준 중복 검증, 실시간 재고 차감, 플랫폼"
    " 수수료 및 등록된 상품 기준 순수익이 자동 정산됩니다."
)

# ⚙️ 플랫폼 수수료율 설정
with st.expander("⚙️ 플랫폼 수수료율 상세 설정 (클릭하여 열기)", expanded=False):
  col_f1, col_f2, col_f3, col_f4, col_f5, col_f6 = st.columns(6)
  with col_f1:
    fee_smart = st.number_input(
        "스마트스토어", value=5.80, step=0.1, format="%.2f"
    )
  with col_f2:
    fee_always = st.number_input("올웨이즈", value=5.50, step=0.1, format="%.2f")
  with col_f3:
    fee_coupang = st.number_input("쿠팡", value=10.80, step=0.1, format="%.2f")
  with col_f4:
    fee_gmarket = st.number_input("지마켓", value=13.00, step=0.1, format="%.2f")
  with col_f5:
    fee_auction = st.number_input("옥션", value=13.00, step=0.1, format="%.2f")
  with col_f6:
    fee_kakao = st.number_input(
        "카카오쇼핑하기", value=10.00, step=0.1, format="%.2f"
    )

fee_rates = {
    "스마트스토어": fee_smart / 100.0,
    "네이버": fee_smart / 100.0,
    "올웨이즈": fee_always / 100.0,
    "쿠팡": fee_coupang / 100.0,
    "지마켓": fee_gmarket / 100.0,
    "G마켓": fee_gmarket / 100.0,
    "옥션": fee_auction / 100.0,
    "카카오쇼핑하기": fee_kakao / 100.0,
    "카카오": fee_kakao / 100.0,
}

st.markdown("---")

# --- [상단 고정 누적 매출 및 순수익 대시보드] ---
st.subheader("📊 [누적 데이터] 전체 매출 및 순수익 요약 대시보드")

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
      "원가+배송+수수료 합계",
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

  with st.expander("🛒 플랫폼별 및 일자별 상세 내역 보기"):
    target_platforms = [
        "스마트스토어",
        "옥션",
        "지마켓",
        "올웨이즈",
        "쿠팡",
        "카카오쇼핑하기",
    ]
    st.markdown("##### 플랫폼별 누적 현황")
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
        .reindex(target_platforms)
        .fillna(0)
        .reset_index()
    )
    st.dataframe(platform_summary, use_container_width=True)

    st.markdown("##### 업로드 일자별 누적 현황")
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
else:
  st.info(
      "아직 업로드 및 반영된 데이터가 없습니다. 아래에서 발주서 파일을 업로드해"
      " 주세요."
  )

st.markdown("---")

# --- [상품 마스터 및 재고 관리 섹션] ---
tab_inv, tab_prod = st.tabs(["📦 실시간 재고 관리", "🏷️ 상품 마스터 관리 (신규 등록)"])

with tab_inv:
  st.write("현재 창고에 남아 있는 상품별 실시간 재고 현황입니다.")
  inv_df = pd.DataFrame(
      list(st.session_state["inventory"].items()),
      columns=["상품명", "현재고수량"],
  )
  st.dataframe(inv_df, use_container_width=True)

  with st.form("inventory_form"):
    st.write("🔧 재고 수동 조정")
    col_i1, col_i2, col_i3 = st.columns([3, 2, 1])
    with col_i1:
      selected_item = st.selectbox(
          "상품 선택", list(st.session_state["inventory"].keys())
      )
    with col_i2:
      add_qty = st.number_input(
          "입고/조정 수량 (+/-)", value=0, step=1, format="%d"
      )
    with col_i3:
      submitted_inv = st.form_submit_button("재고 반영")
    if submitted_inv and add_qty != 0:
      st.session_state["inventory"][selected_item] += add_qty
      st.success(f"{selected_item} 재고가 성공적으로 반영되었습니다!")
      st.rerun()

with tab_prod:
  st.write(
      "등록된 상품들의 판매가, 원가, 배송비 기준을 확인하거나 새로운 상품을"
      " 추가할 수 있습니다."
  )
  prod_list = []
  for p_name, p_info in st.session_state["product_master"].items():
    prod_list.append({
        "상품명": p_name,
        "판매가": p_info["selling_price"],
        "원가": p_info["cost_price"],
        "배송비": p_info["shipping_fee"],
        "부가세별도여부": "별도(10%가산)"
        if p_info["vat_separate"]
        else "포함",
    })
  st.dataframe(pd.DataFrame(prod_list), use_container_width=True)

  with st.form("new_product_form"):
    st.write("✨ 신상품 등록 / 기존 상품 수정")
    cp1, cp2, cp3 = st.columns(3)
    with cp1:
      new_p_name = st.text_input("상품명 (옵션 포함 정확히 입력)")
      new_s_price = st.number_input("판매가 (원)", value=10000, step=100)
    with cp2:
      new_c_price = st.number_input("원가 (원)", value=5000, step=100)
      new_ship = st.number_input("배송비 (원)", value=3000, step=100)
    with cp3:
      new_vat = st.checkbox("부가세 별도 (공급가에 10% 추가 계산)")
      new_inv_qty = st.number_input("초기 재고 수량", value=100, step=10)

    submitted_prod = st.form_submit_button("상품 등록/저장하기")
    if submitted_prod and new_p_name:
      st.session_state["product_master"][new_p_name] = {
          "selling_price": new_s_price,
          "cost_price": new_c_price,
          "shipping_fee": new_ship,
          "vat_separate": new_vat,
      }
      if new_p_name not in st.session_state["inventory"]:
        st.session_state["inventory"][new_p_name] = new_inv_qty
      st.success(f"'{new_p_name}' 상품이 성공적으로 등록되었습니다!")
      st.rerun()

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


def calculate_item_finance(product_name, option_name, channel):
  p_str = str(product_name)
  o_str = str(option_name)
  combined_text = p_str + " " + o_str

  matched_key = "기타상품"
  for key in st.session_state["product_master"].keys():
    # 키워드 매칭 (예: 키스틱, 만두, 김말이, 어묵바 세부항목)
    keywords = key.split()
    if all(kw in combined_text for kw in keywords[:2]):
      matched_key = key
      break
    elif "키스틱" in combined_text and "키스틱" in key:
      if "40개" in combined_text and "40개" in key:
        matched_key = key
        break
      elif "100개" in combined_text and "100개" in key:
        matched_key = key
        break
    elif "만두" in combined_text or "고추잡채" in combined_text:
      if "만두" in key or "고추잡채" in key:
        matched_key = key
        break
    elif "김말이" in combined_text and "김말이" in key:
      matched_key = key
      break
    elif "어묵바" in combined_text and "어묵바" in key:
      if "매콤" in combined_text and "매콤" in key:
        matched_key = key
        break
      elif "오징어" in combined_text and "오징어" in key:
        matched_key = key
        break
      elif "체다" in combined_text and "체다" in key:
        matched_key = key
        break
      elif "오리지날" in combined_text and "오리지날" in key:
        matched_key = key
        break

  if matched_key in st.session_state["product_master"]:
    p_info = st.session_state["product_master"][matched_key]
    selling_price = p_info["selling_price"]
    cost_price = p_info["cost_price"]
    shipping_fee = p_info["shipping_fee"]
    item_category = matched_key
  else:
    selling_price = 10000
    cost_price = 5000
    shipping_fee = 3000
    item_category = "기타상품"

  rate = fee_rates.get(channel, 0.10)
  platform_fee = selling_price * rate
  net_profit = selling_price - platform_fee - cost_price - shipping_fee

  return {
      "카테고리": item_category,
      "판매가": selling_price,
      "원가": cost_price,
      "배송비": shipping_fee,
      "플랫폼수수료": platform_fee,
      "순수익": net_profit,
  }


def get_column_value(row, possible_cols, default=""):
  for col in possible_cols:
    if col in row and pd.notna(row[col]):
      return str(row[col])
  return default


def extract_order_date(df):
  """엑셀 파일 내에서 날짜 형태(YYYY-MM-DD 또는 YYYYMMDD)를 탐색"""
  for col in df.columns:
    for val in df[col].dropna().astype(str):
      val_clean = val.strip()
      # 날짜 패턴 탐색 시도 (예: 2026-09-21 또는 26-09-21 등)
      if (
          len(val_clean) >= 8
          and ("-" in val_clean or val_clean.isdigit())
          and ("202" in val_clean or "26" in val_clean)
      ):
        # YYYY-MM-DD 형태로 정규화 시도
        try:
          parsed_date = pd.to_datetime(val_clean, errors="coerce")
          if pd.notna(parsed_date):
            return parsed_date.strftime("%Y-%m-%d")
        except:
          pass
  return datetime.now().strftime("%Y-%m-%d")


def process_custom_orders(shopmoa_df, always_df):
  frames = []
  sales_data_list = []

  # 업로드된 파일들에서 날짜 추출 (우선 순위: 샵모아 -> 올웨이즈 -> 오늘날짜)
  detected_date = None
  for df_target in [shopmoa_df, always_df]:
    if df_target is not None and not df_target.empty:
      detected_date = extract_order_date(df_target)
      if detected_date:
        break
  if not detected_date:
    detected_date = datetime.now().strftime("%Y-%m-%d")

  def parse_dataframe(df, default_channel_name):
    if df is None or df.empty:
      return
    for _, row in df.iterrows():
      detected_channel = default_channel_name
      row_str = " ".join([str(val) for val in row.values])

      if "쿠팡" in row_str:
        detected_channel = "쿠팡"
      elif "스마트스토어" in row_str or "네이버" in row_str:
        detected_channel = "스마트스토어"
      elif "지마켓" in row_str or "G마켓" in row_str:
        detected_channel = "지마켓"
      elif "옥션" in row_str:
        detected_channel = "옥션"
      elif "카카오" in row_str or "쇼핑하기" in row_str:
        detected_channel = "카카오쇼핑하기"
      elif "올웨이즈" in row_str:
        detected_channel = "올웨이즈"

      if default_channel_name == "샵모아":
        sname = get_column_value(row, ["수취인명", "수령인", "받는분성명"])
        phone = get_column_value(
            row, ["수취인 전화번호", "수령인 연락처", "전화번호"]
        )
        mobile = get_column_value(
            row, ["수취인 핸드폰번호", "수령인 핸드폰", "휴대폰번호", "핸드폰"]
        )
        if not mobile:
          mobile = phone
        zipcode = get_column_value(row, ["우편번호"])
        address = get_column_value(row, ["수취인주소", "주소"])
        p_name = get_column_value(row, ["상품명"])
        opt_name = get_column_value(row, ["옵션", "상품옵션"])
        qty_val = get_column_value(row, ["수량", "주문수량"], "1")
        qty = int(pd.to_numeric(qty_val, errors="coerce") or 1)
        msg = get_column_value(row, ["배송메세지", "배송메모", "고객요청사항"])
        order_id = get_column_value(row, ["주문번호", "주문아이디"])
        invoice_no = get_column_value(
            row, ["송장번호", "택배송장번호", "운송장번호"]
        )
      else:
        sname = get_column_value(row, ["수령인", "수취인명"])
        phone = get_column_value(row, ["수령인 연락처", "전화번호"])
        mobile = get_column_value(row, ["수령인 핸드폰", "핸드폰", "휴대폰번호"])
        if not mobile:
          mobile = phone
        zipcode = get_column_value(row, ["우편번호"])
        address = get_column_value(row, ["주소", "수취인주소"])
        p_name = get_column_value(row, ["상품명"])
        opt_name = get_column_value(row, ["옵션", "상품옵션"])
        qty_val = get_column_value(row, ["수량", "주문수량"], "1")
        qty = int(pd.to_numeric(qty_val, errors="coerce") or 1)
        msg = get_column_value(row, ["배송메모", "배송메세지"])
        order_id = get_column_value(row, ["주문아이디", "주문번호"])
        invoice_no = get_column_value(
            row, ["송장번호", "택배송장번호", "운송장번호"]
        )

      fin = calculate_item_finance(p_name, opt_name, detected_channel)

      for _ in range(max(1, qty)):
        sales_data_list.append({
            "업로드일자": detected_date,
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
          "송장번호": invoice_no,
          "주문일": detected_date,
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
        detected_date,
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
          "송장번호": row["송장번호"],
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
          "배송메모": row["배송메세지1"],
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
          "송장번호": row["송장번호"],
      }

    # 어묵바 분기 (가람식품)
    if "어묵바" in p_name or "어묵바" in opt_name:
      target_name = "오리지날 부산어묵바 80g x 10개"
      if "매콤달콤" in opt_name or "매콤한맛" in p_name:
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
        if target_name in st.session_state["inventory"]:
          st.session_state["inventory"][target_name] -= 1

    # 키스틱 분기
    elif "키스틱" in p_name or "키스틱" in opt_name:
      is_40 = "40개" in p_name or "40개" in opt_name
      base_name = str(row["원격_받는분성명"])

      if is_40:
        if qty == 2:
          r_copy = create_standard_row(base_name, 1)
          r_copy["상품명"] = "키스틱 15g x 100개"
          kistic_rows.append(r_copy)
          if "키스틱 15g x 100개" in st.session_state["inventory"]:
            st.session_state["inventory"]["키스틱 15g x 100개"] -= 1
        elif qty == 3:
          r1 = create_standard_row(base_name, 1)
          r1["상품명"] = "키스틱 15g x 40개"
          kistic_rows.append(r1)
          r2 = create_standard_row(f"{base_name}2", 1)
          r2["상품명"] = "키스틱 15g x 100개"
          kistic_rows.append(r2)
          if "키스틱 15g x 40개" in st.session_state["inventory"]:
            st.session_state["inventory"]["키스틱 15g x 40개"] -= 1
          if "키스틱 15g x 100개" in st.session_state["inventory"]:
            st.session_state["inventory"]["키스틱 15g x 100개"] -= 1
        else:
          r_copy = create_standard_row(base_name, qty)
          r_copy["상품명"] = "키스틱 15g x 40개"
          kistic_rows.append(r_copy)
          if "키스틱 15g x 40개" in st.session_state["inventory"]:
            st.session_state["inventory"]["키스틱 15g x 40개"] -= qty
      else:
        r_copy = create_standard_row(base_name, qty)
        r_copy["상품명"] = "키스틱 15g x 100개"
        kistic_rows.append(r_copy)
        if "키스틱 15g x 100개" in st.session_state["inventory"]:
          st.session_state["inventory"]["키스틱 15g x 100개"] -= qty

    # 만두 분기
    elif "만두" in p_name or "고추잡채" in p_name:
      base_name = str(row["원격_받는분성명"])
      r_copy = create_standard_row(base_name, qty)
      r_copy["상품명"] = "더 바삭한 중화 고추잡채 군만두 1.2kg"
      frozen_rows.append(r_copy)
      if "더 바삭한 중화 고추잡채 군만두 1.2kg" in st.session_state["inventory"]:
        st.session_state["inventory"][
            "더 바삭한 중화 고추잡채 군만두 1.2kg"
        ] -= qty

    # 김말이 분기
    elif "김말이" in p_name:
      base_name = str(row["원격_받는분성명"])
      r_copy = create_standard_row(base_name, qty * 3)
      r_copy["상품명"] = "김말이튀김400g"
      frozen_rows.append(r_copy)
      if "김말이튀김400g" in st.session_state["inventory"]:
        st.session_state["inventory"]["김말이튀김400g"] -= qty * 3

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
      "송장번호",
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

  return garam_df, kistic_df, frozen_df, sales_df, detected_date


# 2. 실행 및 다운로드 버튼 섹션
st.markdown("---")
st.subheader("2. 맞춤형 발주서 변환 및 누적 데이터 반영 실행")

col_btn1, col_btn2, col_btn3 = st.columns([2, 2, 1])

with col_btn1:
  run_clicked = st.button(
      "🚀 발주서 변환 및 재고차감/누적 반영", type="primary"
  )

with col_btn2:
  current_date_str = datetime.now().strftime("%Y-%m-%d")
  zip_buffer = io.BytesIO()
  with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
    if not st.session_state["accumulated_garam"].empty:
      g_io = io.BytesIO()
      with pd.ExcelWriter(g_io, engine="openpyxl") as writer:
        st.session_state["accumulated_garam"].to_excel(writer, index=False)
      zip_file.writestr(
          f"가람식품_통합누적_발주서_{current_date_str}.xlsx", g_io.getvalue()
      )

    if not st.session_state["accumulated_kistic"].empty:
      k_io = io.BytesIO()
      with pd.ExcelWriter(k_io, engine="openpyxl") as writer:
        st.session_state["accumulated_kistic"].to_excel(writer, index=False)
      zip_file.writestr(
          f"키스틱_통합누적_발주서_{current_date_str}.xlsx", k_io.getvalue()
      )

    if not st.session_state["accumulated_frozen"].empty:
      f_io = io.BytesIO()
      with pd.ExcelWriter(f_io, engine="openpyxl") as writer:
        st.session_state["accumulated_frozen"].to_excel(writer, index=False)
      zip_file.writestr(
          f"냉동식품_통합누적_발주서_{current_date_str}.xlsx", f_io.getvalue()
      )
  zip_buffer.seek(0)

  st.download_button(
      label="📥 누적 통합 발주서 ZIP 다운로드",
      data=zip_buffer,
      file_name=f"마켓지니_전체누적_통합발주서_{current_date_str}.zip",
      mime="application/zip",
  )

with col_btn3:
  if st.button("🧹 전체 초기화"):
    st.session_state["accumulated_sales"] = pd.DataFrame()
    st.session_state["accumulated_garam"] = pd.DataFrame()
    st.session_state["accumulated_kistic"] = pd.DataFrame()
    st.session_state["accumulated_frozen"] = pd.DataFrame()
    st.success("초기화 완료")
    st.rerun()

if run_clicked:
  if shopmoa_file is None and always_file is None:
    st.warning("최소 한 개 이상의 발주서 파일을 업로드해 주세요.")
  else:
    try:
      s_df = pd.read_excel(shopmoa_file) if shopmoa_file else None
      a_df = pd.read_excel(always_file) if always_file else None

      # 1차 파싱하여 파일 내 날짜 먼저 감지
      _, _, _, _, detected_date = process_custom_orders(s_df, a_df)

      # 중복 업로드 검증 (이미 해당 날짜 데이터가 누적 sales에 존재하는지 확인)
      existing_sales = st.session_state["accumulated_sales"]
      if not existing_sales.empty and detected_date in existing_sales[
          "업로드일자"
        ].astype(str).values:
        st.error(
            f"⚠️ [중복 업로드 방지] 이미 '{detected_date}' 일자의 발주서 데이터가"
            " 누적 반영되어 있습니다. 동일한 파일은 중복 적용되지 않습니다."
        )
      else:
        garam_df, kistic_df, frozen_df, sales_df, date_str = (
            process_custom_orders(s_df, a_df)
        )

        if not sales_df.empty:
          st.session_state["accumulated_sales"] = pd.concat(
              [st.session_state["accumulated_sales"], sales_df],
              ignore_index=True,
          )
        if not garam_df.empty:
          st.session_state["accumulated_garam"] = pd.concat(
              [st.session_state["accumulated_garam"], garam_df],
              ignore_index=True,
          )
        if not kistic_df.empty:
          st.session_state["accumulated_kistic"] = pd.concat(
              [
                  st.session_state["accumulated_kistic"],
                  kistic_df,
              ],
              ignore_index=True,
          )
        if not frozen_df.empty:
          st.session_state["accumulated_frozen"] = pd.concat(
              [
                  st.session_state["accumulated_frozen"],
                  frozen_df,
              ],
              ignore_index=True,
          )

        st.success(
            f"✨ [날짜: {date_str}] 발주서가 성공적으로 분석되어 재고 차감 및"
            " 누적 반영되었습니다!"
        )
        st.rerun()

    except Exception as e:
      st.error(f"파일 처리 중 오류가 발생했습니다: {e}")
