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

# 상품 마스터 관리 (출고 거래처 필드 'vendor_type' 추가)
if "product_master" not in st.session_state:
    st.session_state["product_master"] = {
        "키스틱 15g x 40개": {
            "selling_price": 9900,
            "cost_price": 113 * 40,
            "shipping_fee": 2900,
            "vat_separate": False,
            "vendor_type": "키스틱",
        },
        "키스틱 15g x 100개": {
            "selling_price": 19900,
            "cost_price": 113 * 100,
            "shipping_fee": 2900,
            "vat_separate": False,
            "vendor_type": "키스틱",
        },
        "더 바삭한 중화 고추잡채 군만두 1.2kg": {
            "selling_price": 13900,
            "cost_price": 4700,
            "shipping_fee": 3900,
            "vat_separate": False,
            "vendor_type": "냉동식품",
        },
        "김말이튀김400g": {
            "selling_price": 13900,
            "cost_price": 1700 * 3,
            "shipping_fee": 3900,
            "vat_separate": False,
            "vendor_type": "냉동식품",
        },
        "오리지날 부산어묵바 80g x 10개": {
            "selling_price": 18900,
            "cost_price": int(536 * 1.1 * 10),
            "shipping_fee": 4300,
            "vat_separate": True,
            "vendor_type": "가람식품",
        },
        "매콤달콤 부산어묵바 80g x 10개": {
            "selling_price": 19900,
            "cost_price": int(560 * 1.1 * 10),
            "shipping_fee": 4300,
            "vat_separate": True,
            "vendor_type": "가람식품",
        },
        "오징어야채 부산어묵바 80g x 10개": {
            "selling_price": 20900,
            "cost_price": int(575 * 1.1 * 10),
            "shipping_fee": 4300,
            "vat_separate": True,
            "vendor_type": "가람식품",
        },
        "체다치즈 부산어묵바 80g x 10개": {
            "selling_price": 21900,
            "cost_price": int(646 * 1.1 * 10),
            "shipping_fee": 4300,
            "vat_separate": True,
            "vendor_type": "가람식품",
        },
    }

st.title("📦 마켓지니 판매 및 재고 관리 프로그램")
st.write("발주서 업로드 시 파일 내 날짜 기준 중복 검증, 원본 데이터 영구 저장, 그리고 마스터 연동 출고처 자동 분류가 지원됩니다.")

# ⚙ 플랫폼 수수료율 설정
with st.expander("⚙ 플랫폼 수수료율 상세 설정 (클릭하여 열기)", expanded=False):
    col_f1, col_f2, col_f3, col_f4, col_f5, col_f6 = st.columns(6)
    with col_f1:
        fee_smart = st.number_input("스마트스토어", value=5
