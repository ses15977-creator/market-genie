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
        fee_smart = st.number_input("스마트스토어", value=5.80, step=0.1, format="%.2f")
    with col_f2:
        fee_always = st.number_input("올웨이즈", value=5.50, step=0.1, format="%.2f")
    with col_f3:
        fee_coupang = st.number_input("쿠팡", value=10.80, step=0.1, format="%.2f")
    with col_f4:
        fee_gmarket = st.number_input("지마켓", value=13.00, step=0.1, format="%.2f")
    with col_f5:
        fee_auction = st.number_input("옥션", value=13.00, step=0.1, format="%.2f")
    with col_f6:
        fee_kakao = st.number_input("카카오쇼핑하기", value=10.00, step=0.1, format="%.2f")

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
    m3.metric("원가+배송+수수료 합계", f"{(total_cost + total_shipping + total_platform_fee):,.0f} 원")
    m4.metric("누적 총 순수익", f"{total_net_profit:,.0f} 원",
              delta=(f"마진율 {(total_net_profit/total_revenue*100):.1f}%" if total_revenue > 0 else "0%"))

    with st.expander("🛒 플랫폼별 및 일자별 상세 내역 보기"):
        target_platforms = ["스마트스토어", "옥션", "지마켓", "올웨이즈", "쿠팡", "카카오쇼핑하기"]
        st.markdown("##### 플랫폼별 누적 현황")
        platform_summary = (
            acc_sales.groupby("판매처")
            .agg(주문건수=("판매가", "count"), 총판매가=("판매가", "sum"), 총원가=("원가", "sum"), 총배송비=("배송비", "sum"), 플랫폼수수료합계=("플랫폼수수료", "sum"), 총순수익=("순수익", "sum"))
            .reindex(target_platforms).fillna(0).reset_index()
        )
        st.dataframe(platform_summary, use_container_width=True)

        st.markdown("##### 업로드 일자별 누적 현황")
        date_summary = acc_sales.groupby("업로드일자").agg(주문건수=("판매가", "count"), 매출액=("판매가", "sum"), 순수익=("순수익", "sum")).reset_index()
        st.dataframe(date_summary, use_container_width=True)
else:
    st.info("아직 업로드 및 반영된 데이터가 없습니다. 아래에서 발주서 파일을 업로드해 주세요.")

st.markdown("---")

# --- [상품 마스터 및 재고 관리 섹션] ---
tab_inv, tab_prod, tab_history = st.tabs(["📦 실시간 재고 관리", "🏷 상품 마스터 관리 (출고처 설정)", "📥 등록된 원본 발주서 확인 및 재다운로드"])

with tab_inv:
    st.write("현재 창고에 남아 있는 상품별 실시간 재고 현황입니다.")
    inv_df = pd.DataFrame(list(st.session_state["inventory"].items()), columns=["상품명", "현재고수량"])
    st.dataframe(inv_df, use_container_width=True)

    with st.form("inventory_form"):
        st.write("🔧 재고 수동 조정")
        col_i1, col_i2, col_i3 = st.columns([3, 2, 1])
        with col_i1:
            selected_item = st.selectbox("상품 선택", list(st.session_state["inventory"].keys()))
        with col_i2:
            add_qty = st.number_input("입고/조정 수량 (+/-)", value=0, step=1, format="%d")
        with col_i3:
            submitted_inv = st.form_submit_button("재고 반영")
        
        if submitted_inv and add_qty != 0:
            st.session_state["inventory"][selected_item] += add_qty
            st.success(f"{selected_item} 재고가 성공적으로 반영되었습니다!")
            st.rerun()

with tab_prod:
    st.write("등록된 상품들의 판매가, 원가, 배송비 및 **출고 거래처**를 관리할 수 있습니다.")
    prod_list = []
    for p_name, p_info in st.session_state["product_master"].items():
        prod_list.append({
            "상품명": p_name,
            "판매가": p_info["selling_price"],
            "원가": p_info["cost_price"],
            "배송비": p_info["shipping_fee"],
            "출고거래처": p_info.get("vendor_type", "키스틱"),
            "부가세별도여부": ("별도(10%가산)" if p_info["vat_separate"] else "포함"),
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
            new_vendor = st.selectbox("출고 거래처 분류", ["가람식품", "키스틱", "냉동식품"])
            new_vat = st.checkbox("부가세 별도 (공급가에 10% 추가 계산)")
            new_inv_qty = st.number_input("초기 재고 수량", value=100, step=10)

        submitted_prod = st.form_submit_button("상품 등록/저장하기")
        if submitted_prod and new_p_name:
            st.session_state["product_master"][new_p_name] = {
                "selling_price": new_s_price, "cost_price": new_c_price, "shipping_fee": new_ship, 
                "vat_separate": new_vat, "vendor_type": new_vendor
            }
            if new_p_name not in st.session_state["inventory"]:
                st.session_state["inventory"][new_p_name] = new_inv_qty
            st.success(f"'{new_p_name}' 상품이 [{new_vendor}] 출고처로 등록되었습니다!")
            st.rerun()

with tab_history:
    st.write("📌 시스템에 반영된 원본 발주서 내역입니다. 날짜별로 다시 엑셀 파일로 다운로드할 수 있습니다.")
    raw_data = st.session_state["accumulated_raw_orders"]
    if not raw_data.empty:
        st.dataframe(raw_data, use_container_width=True)
        unique_dates = raw_data["업로드일자"].unique()
        selected_date_dl = st.selectbox("다운로드할 업로드 일자 선택", unique_dates)

        if selected_date_dl:
            sub_df = raw_data[raw_data["업로드일자"] == selected_date_dl]
            output_io = io.BytesIO()
            with pd.ExcelWriter(output_io, engine="openpyxl") as writer:
                sub_df.to_excel(writer, index=False)
            output_io.seek(0)
            st.download_button(
                label=f"📥 [{selected_date_dl}] 업로드 원본 발주서 엑셀 다운로드",
                data=output_io,
                file_name=f"마켓지니_원본발주서_{selected_date_dl}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    else:
        st.info("아직 저장된 업로드 원본 발주서 데이터가 없습니다.")

st.markdown("---")

# 1. 파일 업로드 섹션
st.subheader("1. 발주서 파일 업로드")
col1, col2 = st.columns(2)

with col1:
    shopmoa_file = st.file_uploader("샵모아 / 통합 발주서 파일 (.xlsx)", type=["xlsx", "xls"], key="shopmoa")

with col2:
    always_file = st.file_uploader("올웨이즈 발주서 파일 (.xlsx)", type=["xlsx", "xls"], key="always")

def match_product_master(product_name, option_name):
    p_str, o_str = str(product_name), str(option_name)
    combined_text = p_str + " " + o_str
    matched_key = next((k for k in st.session_state["product_master"] if k in combined_text), None)

    if not matched_key:
        for key in st.session_state["product_master"].keys():
            if any(kw in combined_text for kw in key.split() if len(kw) > 1):
                matched_key = key
                break

    if matched_key:
        return matched_key, st.session_state["product_master"][matched_key]
    return "기타상품", {"selling_price": 10000, "cost_price": 5000, "shipping_fee": 3000, "vat_separate": False, "vendor_type": "키스틱"}

def get_column_value(row, possible_cols, default=""):
    for col in possible_cols:
        if col in row and pd.notna(row[col]):
            return str(row[col])
    return default

def extract_order_date(df):
    for col in df.columns:
        for val in df[col].dropna().astype(str):
            val_clean = val.strip()
            if len(val_clean) >= 8 and ("-" in val_clean or val_clean.isdigit()) and ("202" in val_clean or "26" in val_clean):
                try:
                    parsed_date = pd.to_datetime(val_clean, errors="coerce")
                    if pd.notna(parsed_date):
                        return parsed_date.strftime("%Y-%m-%d")
                except: pass
    return datetime.now().strftime("%Y-%m-%d")

def process_custom_orders(shopmoa_df, always_df):
    frames, sales_data_list, raw_rows_list = [], [], []
    detected_date = extract_order_date(shopmoa_df) if shopmoa_df is not None and not shopmoa_df.empty else None
    if not detected_date and always_df is not None and not always_df.empty:
        detected_date = extract_order_date(always_df)
    if not detected_date:
        detected_date = datetime.now().strftime("%Y-%m-%d")

    def parse_dataframe(df, default_channel_name):
        if df is None or df.empty: return
        for _, row in df.iterrows():
            row_str = " ".join([str(val) for val in row.values])
            detected_channel = next((c for c, k in [("쿠팡", "쿠팡"), ("스마트스토어", "스마트스토어"), ("스마트스토어", "네이버"), ("지마켓", "지마켓"), ("지마켓", "G마켓"), ("옥션", "옥션"), ("카카오쇼핑하기", "카카오"), ("카카오쇼핑하기", "쇼핑하기"), ("올웨이즈", "올웨이즈")] if k in row_str), default_channel_name)

            if default_channel_name == "샵모아":
                sname = get_column_value(row, ["수취인명", "수령인", "받는분성명"])
                phone = get_column_value(row, ["수취인 전화번호", "수령인 연락처", "전화번호"])
                mobile = get_column_value(row, ["수취인 핸드폰번호", "수령인 핸드폰", "휴대폰번호", "핸드폰"]) or phone
                zipcode = get_column_value(row, ["우편번호"])
                address = get_column_value(row, ["수취인주소", "주소"])
                p_name = get_column_value(row, ["상품명"])
                opt_name = get_column_value(row, ["옵션", "상품옵션"])
                qty = int(pd.to_numeric(get_column_value(row, ["수량", "주문수량"], "1"), errors="coerce") or 1)
                msg = get_column_value(row, ["배송메세지", "배송메모", "고객요청사항"])
                order_id = get_column_value(row, ["주문번호", "주문아이디"])
                invoice_no = get_column_value(row, ["송장번호", "택배송장번호", "운송장번호"])
            else:
                sname = get_column_value(row, ["수령인", "수취인명"])
                phone = get_column_value(row, ["수령인 연락처", "전화번호"])
                mobile = get_column_value(row, ["수령인 핸드폰", "핸드폰", "휴대폰번호"]) or phone
                zipcode = get_column_value(row, ["우편번호"])
                address = get_column_value(row, ["주소", "수취인주소"])
                p_name = get_column_value(row, ["상품명"])
                opt_name = get_column_value(row, ["옵션", "상품옵션"])
                qty = int(pd.to_numeric(get_column_value(row, ["수량", "주문수량"], "1"), errors="coerce") or 1)
                msg = get_column_value(row, ["배송메모", "배송메세지"])
                order_id = get_column_value(row, ["주문아이디", "주문번호"])
                invoice_no = get_column_value(row, ["송장번호", "택배송장번호", "운송장번호"])

            matched_key, p_info = match_product_master(p_name, opt_name)
            platform_fee = p_info["selling_price"] * fee_rates.get(detected_channel, 0.10)
            net_profit = p_info["selling_price"] - platform_fee - p_info["cost_price"] - p_info["shipping_fee"]

            for _ in range(max(1, qty)):
                sales_data_list.append({"업로드일자": detected_date, "판매처": detected_channel, "주문번호": str(order_id), "상품명": matched_key, "판매가": p_info["selling_price"], "원가": p_info["cost_price"], "배송비": p_info["shipping_fee"], "플랫폼수수료": platform_fee, "순수익": net_profit})

            raw_rows_list.append({"업로드일자": detected_date, "판매처": detected_channel, "주문번호": order_id, "송장번호": invoice_no, "수령인": sname, "전화번호": phone, "휴대폰번호": mobile, "우편번호": zipcode, "주소": address, "상품명": p_name, "옵션": opt_name, "수량": qty, "배송메모": msg})

            frames.append({"원격_받는분성명": sname, "원격_받는분전화번호": phone, "원격_받는분기타연락처": mobile, "원격_받는분우편번호": zipcode, "원격_받는분주소": address, "상품명_원본": p_name, "옵션_원본": opt_name, "상품수량": qty, "배송메세지1": msg, "주문번호": order_id, "송장번호": invoice_no, "주문일": detected_date, "판매처": detected_channel, "매칭상품명": matched_key, "출고거래처": p_info.get("vendor_type", "키스틱")})

    parse_dataframe(shopmoa_df, "샵모아")
    parse_dataframe(always_df, "올웨이즈")

    if not frames: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), detected_date

    garam_rows, kistic_rows, frozen_rows = [], [], []
    for _, row in pd.DataFrame(frames).iterrows():
        qty, matched_item, vendor_type, base_name = int(row["상품수량"]), row["매칭상품명"], row["출고거래처"], str(row["원격_받는분성명"])

        def create_garam_row(name, q):
            return {"받는분성명": name, "받는분전화번호": row["원격_받는분전화번호"], "받는분기타연락처": row["원격_받는분기타연락처"], "받는분우편번호": row["원격_받는분우편번호"], "받는분주소": row["원격_받는분주소"], "내품수량": q, "배송메세지1": row["배송메세지1"], "출력일": "", "운임구분": "", "기본운임": "", "고객사용번호": "", "품명": matched_item, "판매처": row["판매처"], "주문번호": row["주문번호"], "송장번호": row["송장번호"], "주문일": row["주문일"], "판매가": "", "정산금액": "", "거래처코드": 16}

        def create_standard_row(name, q, item_name):
            return {"수령자이름": name, "수령자전화": row["원격_받는분전화번호"], "수령자휴대폰": row["원격_받는분기타연락처"], "수령자우편번호": row["원격_받는분우편번호"], "수령자주소": row["원격_받는분주소"], "상품수량": q, "배송메모": row["배송메세지1"], "제조사": "", "카테고리": "", "품절": "", "배송 보류": "", "상품명": item_name, "판매처": row["판매처"], "주문번호": row["주문번호"], "발주일": "", "관리번호": "", "상태": "", "송장번호": row["송장번호"]}

        if vendor_type == "가람식품":
            for i in range(qty):
                garam_rows.append(create_garam_row(f"{base_name}{i+1}" if qty > 1 else base_name, 1))
                if matched_item in st.session_state["inventory"]: st.session_state["inventory"][matched_item] -= 1
        elif vendor_type == "키스틱":
            if "40개" in matched_item and qty == 2:
                kistic_rows.append(create_standard_row(base_name, 1, "키스틱 15g x 100개"))
                if "키스틱 15g x 100개" in st.session_state["inventory"]: st.session_state["inventory"]["키스틱 15g x 100개"] -= 1
            elif "40개" in matched_item and qty == 3:
                kistic_rows.extend([create_standard_row(base_name, 1, "키스틱 15g x 40개"), create_standard_row(f"{base_name}2", 1, "키스틱 15g x 100개")])
                if "키스틱 15g x 40개" in st.session_state["inventory"]: st.session_state["inventory"]["키스틱 15g x 40개"] -= 1
                if "키스틱 15g x 100개" in st.session_state["inventory"]: st.session_state["inventory"]["키스틱 15g x 100개"] -= 1
            else:
                kistic_rows.append(create_standard_row(base_name, qty, matched_item))
                if matched_item in st.session_state["inventory"]: st.session_state["inventory"][matched_item] -= qty
        elif vendor_type == "냉동식품":
            actual_qty = qty * 3 if "김말이" in matched_item else qty
            frozen_rows.append(create_standard_row(
