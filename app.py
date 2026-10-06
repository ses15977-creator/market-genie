from datetime import datetime
import io
import zipfile
import pandas as pd
import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="마켓지니 통합 판매관리 프로그램", page_icon="📦", layout="centered"
)

# 1. 세션 상태 초기화 (누적 데이터 및 재고/상품 마스터/원본 발주서 저장소 관리)
if "accumulated_sales" not in st.session_state:
  st.session_state["accumulated_sales"] = pd.DataFrame()
if "accumulated_garam" not in st.session_state:
  st.session_state["accumulated_garam"] = pd.DataFrame()
if "accumulated_kistic" not in st.session_state:
  st.session_state["accumulated_kistic"] = pd.DataFrame()
if "accumulated_frozen" not in st.session_state:
  st.session_state["accumulated_frozen"] = pd.DataFrame()
if "accumulated_shinyfood" not in st.session_state:
  st.session_state["accumulated_shinyfood"] = pd.DataFrame()
if "accumulated_raw_orders" not in st.session_state:
  st.session_state["accumulated_raw_orders"] = pd.DataFrame()

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

# 상품 마스터 관리 (category 필드 추가: 가람식품, 키스틱, 냉동식품, 신의푸드 중 택 1)
if "product_master" not in st.session_state:
  st.session_state["product_master"] = {
      "키스틱 15g x 40개": {
          "category": "키스틱",
          "selling_price": 9900,
          "cost_price": 113 * 40,
          "shipping_fee": 2900,
          "vat_separate": False,
      },
      "키스틱 15g x 100개": {
          "category": "키스틱",
          "selling_price": 19900,
          "cost_price": 113 * 100,
          "shipping_fee": 2900,
          "vat_separate": False,
      },
      "더 바삭한 중화 고추잡채 군만두 1.2kg": {
          "category": "냉동식품",
          "selling_price": 13900,
          "cost_price": 4700,
          "shipping_fee": 3900,
          "vat_separate": False,
      },
      "김말이튀김400g": {
          "category": "냉동식품",
          "selling_price": 13900,
          "cost_price": 1700 * 3,
          "shipping_fee": 3900,
          "vat_separate": False,
      },
      "오리지날 부산어묵바 80g x 10개": {
          "category": "가람식품",
          "selling_price": 18900,
          "cost_price": int(536 * 1.1 * 10),
          "shipping_fee": 4300,
          "vat_separate": True,
      },
      "매콤달콤 부산어묵바 80g x 10개": {
          "category": "가람식품",
          "selling_price": 19900,
          "cost_price": int(560 * 1.1 * 10),
          "shipping_fee": 4300,
          "vat_separate": True,
      },
      "오징어야채 부산어묵바 80g x 10개": {
          "category": "가람식품",
          "selling_price": 20900,
          "cost_price": int(575 * 1.1 * 10),
          "shipping_fee": 4300,
          "vat_separate": True,
      },
      "체다치즈 부산어묵바 80g x 10개": {
          "category": "가람식품",
          "selling_price": 21900,
          "cost_price": int(646 * 1.1 * 10),
          "shipping_fee": 4300,
          "vat_separate": True,
      },
  }

st.title("📦 마켓지니 판매 및 재고 관리 프로그램")
st.write(
    "발주서 업로드 시 파일 내 날짜 기준 중복 검증, 원본 데이터 영구 저장,"
    " 실시간 재고 차감 및 4개 공급사별 발주서 분류를 지원합니다."
)

# ⚙ 플랫폼 수수료율 설정
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
tab_inv, tab_prod, tab_history = st.tabs([
    "📦 실시간 재고 관리",
    "🏷 상품 마스터 관리 (공급사 카테고리 지정)",
    "📥 등록된 원본 발주서 확인 및 재다운로드",
])

with tab_inv
