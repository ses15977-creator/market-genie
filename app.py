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

# 상품 마스터 관리 (출고 거래처 필드 'vendor_type' 추가: '가람식품', '키스틱', '냉동식품')
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
        "오리지날 부산어묵
