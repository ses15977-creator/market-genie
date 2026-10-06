from datetime import datetime
import io
import zipfile
import pandas as pd
import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="마켓지니 통합 판매관리 프로그램", page_icon="📦", layout="centered"
)

# 1. 세션 상태 초기화 (누적 데이터 및 재고 관리)
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

st.title("📦 마켓지니 판매 및 재고 관리 프로그램")
st.write(
    "발주서 업로드 시 플랫폼별 수수료, 고정 원가·배송비·부가세가 자동 계산되며,"
    " 재고가 실시간 차감되고 정확한 송장 연동 발주서가 생성됩니다."
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

# --- [재고 현황판 및 관리 섹션] ---
with st.expander(
    "📦 실시간 상품별 재고 현황 및 관리 (클릭하여 열기)", expanded=True
):
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

  selling_price = 0
  cost_price = 0
  shipping_fee = 0
  item_category = "기타상품"

  if "키스틱" in combined_text:
    shipping_fee = 2900
    if "40개" in combined_text:
      selling_price = 9900
      cost_price = 113 * 40
      item_category = "키스틱 15g x 40개"
    else:
      selling_price = 19900
      cost_price = 113 * 100
      item_category = "키스틱 15g x 100개"

  elif "만두" in combined_text or "고추잡채" in combined_text:
    shipping_fee = 3900
    selling_price = 13900
    cost_price = 4700
    item_category = "더 바삭한 중화 고추잡채 군만두 1.2kg"

  elif "김말이" in combined_text:
    shipping_fee = 3900
    selling_price = 13900
    cost_price = 1700 * 3
    item_category = "김말이튀김400g"

  elif "어묵바" in combined_text:
    shipping_fee = 4300
    if "매콤달콤" in combined_text or "매콤한맛" in combined_text:
      selling_price = 19900
      cost_price = int(560 * 1.1 * 10)
      item_category = "매콤달콤 부산어묵바 80g x 10개"
    elif "오징어야채" in combined_text:
      selling_price = 20900
      cost_price = int(575 * 1.1 * 10)
      item_category = "오징어야채 부산어묵바 80g x 10개"
    elif "체다치즈" in combined_text:
      selling_price = 21900
      cost_price = int(646 * 1.1 * 10)
      item_category = "체다치즈 부산어묵바 80g x 10개"
    else:
      selling_price = 18900
      cost_price = int(536 * 1.1 * 10)
      item_category = "오리지날 부산어묵바 80g x 10개"
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


def process_custom_orders(shopmoa_df, always_df):
  frames = []
  sales_data_list = []
  date_str = datetime.now().strftime("%Y-%m-%d")

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
        detected_channel
