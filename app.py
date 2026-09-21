import datetime
import io
import os
import zipfile
import pandas as pd
import streamlit as st

# 페이지 설정 및 디자인 테마
st.set_page_config(
    page_title="마켓지니 마켓관리 프로그램", page_icon="📈", layout="wide"
)

# Custom CSS
st.markdown(
    """
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button {
        background-color: #ff4b4b;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        height: 3em;
        width: 100%;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("🌟 마켓지니 마켓관리 프로그램")
st.markdown(
    "**샵모아** 및 **올웨이즈** 주문 파일을 업로드하면, 지정된 고정 판매가와 원가로"
    " **매출·순이익·수수료**를 계산하고 일자/월별로 자동 누적 관리합니다!"
)
st.markdown("---")

# 누적 데이터 저장 파일 경로
DB_FILE = "market_history.csv"


# 누적 데이터 불러오기 함수
def load_history():
  if os.path.exists(DB_FILE):
    try:
      df = pd.read_csv(DB_FILE)
      if "날짜" in df.columns:
        return df
    except:
      pass
  return pd.DataFrame(
      columns=[
          "날짜",
          "판매처",
          "상품명",
          "수량",
          "매출액",
          "원가",
          "배송비",
          "수수료",
          "순이익",
      ]
  )


# 누적 데이터 저장 함수
def save_history(new_df):
  existing_df = load_history()
  if not existing_df.empty and not new_df.empty:
    combined = pd.concat([existing_df, new_df], ignore_index=True)
    combined.to_csv(DB_FILE, index=False, encoding="utf-8-sig")
  elif not new_df.empty:
    new_df.to_csv(DB_FILE, index=False, encoding="utf-8-sig")


# 파일 업로드 섹션 (모바일 호환성을 위해 지원 확장자 확대 및 안내 추가)
col_up1, col_up2 = st.columns(2)
with col_up1:
  st.subheader("🛒 샵모아 주문 파일")
  shopmoa_file = st.file_uploader(
      "샵모아 엑셀 업로드", type=["xlsx", "xls", "csv"], key="shop"
  )
with col_up2:
  st.subheader("🚀 올웨이즈 주문 파일")
  always_file = st.file_uploader(
      "올웨이즈 엑셀 업로드", type=["xlsx", "xls", "csv"], key="always"
  )

# 오늘 날짜 (기본 세팅용)
today_date_str = datetime.datetime.now().strftime("%Y-%m-%d")
selected_order_date = st.date_input(
    "📅 이번 정산(주문) 데이터의 날짜를 선택하세요",
    datetime.datetime.strptime(today_date_str, "%Y-%m-%d"),
)
order_date_str = selected_order_date.strftime("%Y-%m-%d")

if st.button("🚀 발주서 변환 및 마켓 정산 분석 시작"):
  if shopmoa_file is None and always_file is None:
    st.warning("엑셀 파일을 최소한 하나 이상 업로드해 주세요!")
  else:
    all_rows = []
    read_success = True

    try:
      # 1. 샵모아 파일 읽기 (모바일 스트림 안정화 처리: io.BytesIO 사용)
      if shopmoa_file:
        bytes_data = shopmoa_file.getvalue()
        try:
          df_shop = pd.read_excel(io.BytesIO(bytes_data))
        except Exception:
          # 혹시 xlsx가 안되면 csv 형태로 재시도 방어 코드
          df_shop = pd.read_csv(io.BytesIO(bytes_data))

        for _, row in df_shop.iterrows():
          site_name = "샵모아"
          for col in ["사이트", "판매처", "쇼핑몰", "마켓명"]:
            if col in df_shop.columns and pd.notna(row.get(col)):
              site_name = str(row.get(col))
              break

          all_rows.append({
              "주문번호": str(row.get("주문번호", "")),
              "판단기준텍스트": str(row.get("상품명", "")),
              "상품명": str(row.get("상품명", "")),
              "수량": int(row.get("수량", 1))
              if pd.notna(row.get("수량"))
              else 1,
              "수취인명": str(row.get("수취인명", "")),
              "전화번호": str(row.get("수취인 전화번호", "")),
              "휴대폰번호": str(row.get("수취인 핸드폰번호", "")),
              "주소": str(row.get("수취인주소", "")),
              "우편번호": str(row.get("우편번호", "")),
              "배송메모": str(row.get("배송메세지", "")),
              "판매처": site_name,
          })

      # 2. 올웨이즈 파일 읽기 (모바일 스트림 안정화 처리: io.BytesIO 사용)
      if always_file:
        bytes_data_alw = always_file.getvalue()
        try:
          df_alw = pd.read_excel(io.BytesIO(bytes_data_alw))
        except Exception:
          df_alw = pd.read_csv(io.BytesIO(bytes_data_alw))

        for _, row in df_alw.iterrows():
          all_rows.append({
              "주문번호": str(row.get("주문아이디", "")),
              "판단기준텍스트": str(row.get("옵션", "")),
              "상품명": str(row.get("상품명", "")),
              "수량": int(row.get("수량", 1))
              if pd.notna(row.get("수량"))
              else 1,
              "수취인명": str(row.get("수령인", "")),
              "전화번호": str(row.get("수령인 연락처", "")),
              "휴대폰번호": "",
              "주소": str(row.get("주소", "")),
              "우편번호": str(row.get("우편번호", "")),
              "배송메모": "",
              "판매처": "올웨이즈",
          })

    except Exception as e:
      read_success = False
      st.error(
          f"파일을 읽는 도중 오류가 발생했습니다. 파일 형식을 확인해주세요. (상세"
          f" 에러: {e})"
      )

    if read_success and all_rows:
      master_df = pd.DataFrame(all_rows)

      냉동_rows = []
      키스틱_rows = []
      가람식품_rows = []
      current_batch_financial = []

      for _, r in master_df.iterrows():
        check_text = r["판단기준텍스트"]
        p_name = r["상품명"]
        orig_qty = r["수량"]
        base_name = r["수취인명"]
        platform = r["판매처"]

        # ----------------------------------------------------
        # 1. 키스틱 처리 (고정 판매가 및 원가)
        # ----------------------------------------------------
        if "키스틱" in check_text:
          sets_100 = orig_qty // 2
          rem_40 = orig_qty % 2

          cost_40 = 113 * 40
          cost_100 = 113 * 100
          price_40 = 9900
          price_100 = 19900
          deliv_per_unit = 2900

          for _ in range(sets_100):
            current_batch_financial.append({
                "날짜": order_date_str,
                "판매처": platform,
                "상품명": "키스틱 100개입",
                "수량": 1,
                "매출액": price_100,
                "원가": cost_100,
                "배송비": deliv_per_unit,
            })

          for _ in range(rem_40):
            current_batch_financial.append({
                "날짜": order_date_str,
                "판매처": platform,
                "상품명": "키스틱 40개입",
                "수량": 1,
                "매출액": price_40,
                "원가": cost_40,
                "배송비": deliv_per_unit,
            })

        # ----------------------------------------------------
        # 2. 어묵바 처리 (가람식품)
        # ----------------------------------------------------
        elif "어묵" in check_text:
          norm_name = "부산어묵 오리지날 어묵바 80g x 10개"
          single_cost_ex = 536
          fixed_price = 18900

          if "매콤" in check_text:
            norm_name = "부산어묵 매콤달콤어묵바 80g x 10개"
            single_cost_ex = 560
            fixed_price = 19900
          elif "오징어" in check_text:
            norm_name = "부산어묵 오징어야채 어묵바 80g x 10개"
            single_cost_ex = 575
            fixed_price = 20900
          elif "체다" in check_text or "치즈" in check_text:
            norm_name = "부산어묵 체다치즈맛 어묵바 80g x 10개"
            single_cost_ex = 646
            fixed_price = 21900

          net_cost = single_cost_ex * 1.1
          deliv_per_unit = 4300

          for i in range(1, orig_qty + 1):
            current_batch_financial.append({
                "날짜": order_date_str,
                "판매처": platform,
                "상품명": norm_name,
                "수량": 1,
                "매출액": fixed_price,
                "원가": net_cost,
                "배송비": deliv_per_unit,
            })

        # ----------------------------------------------------
        # 3. 냉동 품목 (고추잡채만두 등)
        # ----------------------------------------------------
        else:
          norm_frozen_name = p_name
          single_cost = 0
          fixed_price = 13900
          deliv_per_unit = 3900

          if (
              "고추잡채" in check_text
              or "만두" in check_text
              or "고추잡채" in p_name
          ):
            norm_frozen_name = "고추잡채군만두 1.2kg"
            single_cost = 4700
            fixed_price = 13900
          elif "김말이" in check_text or "김말이" in p_name:
            norm_frozen_name = "김말이 튀김 400g"
            single_cost = 1700
            fixed_price = 10000

          for _ in range(orig_qty):
            current_batch_financial.append({
                "날짜": order_date_str,
                "판매처": platform,
                "상품명": norm_frozen_name,
                "수량": 1,
                "매출액": fixed_price,
                "원가": single_cost,
                "배송비": deliv_per_unit,
            })

      df_current_batch = pd.DataFrame(current_batch_financial)
      if not df_current_batch.empty:

        def get_comm(row):
          p = str(row["판매처"])
          rev = row["매출액"]
          if "올웨이즈" in p:
            return rev * 0.07
          else:
            return rev * 0.055

        df_current_batch["수수료"] = df_current_batch.apply(get_comm, axis=1)
        df_current_batch["순이익"] = (
            df_current_batch["매출액"]
            - df_current_batch["원가"]
            - df_current_batch["배송비"]
            - df_current_batch["수수료"]
        )
        save_history(df_current_batch)

      st.success("✅ 업로드 파일 정산 및 누적 데이터 저장 완료!")

# ----------------------------------------------------
# 📊 상단 대시보드 및 누적 데이터 조회 섹션
# ----------------------------------------------------
st.markdown("---")
st.header("📈 마켓지니 종합 매출 & 순이익 대시보드")

history_df = load_history()

if not history_df.empty:
  history_df["날짜"] = pd.to_datetime(history_df["날짜"])
  history_df["년월"] = history_df["날짜"].dt.strftime("%Y-%m")

  current_year_month = datetime.datetime.now().strftime("%Y-%m")
  this_month_df = history_df[history_df["년월"] == current_year_month]
  this_month_sales = this_month_df["매출액"].sum()
  this_month_profit = this_month_df["순이익"].sum()

  c1, c2, c3 = st.columns(3)
  with c1:
    st.metric(
        label=f"📅 {current_year_month} 이번 달 누적 매출",
        value=f"{int(this_month_sales):,} 원",
    )
  with c2:
    st.metric(
        label=f"✨ {current_year_month} 이번 달 누적 순이익",
        value=f"{int(this_month_profit):,} 원",
    )
  with c3:
    total_all_sales = history_df["매출액"].sum()
    st.metric(
        label="🏆 전체 누적 총매출", value=f"{int(total_all_sales):,} 원"
    )

  st.markdown("---")
  st.subheader("🔍 일자별 / 월별 누적 데이터 검색 및 필터")

  f_col1, f_col2 = st.columns(2)
  with f_col1:
    search_mode = st.radio("조회 기준 선택", ["월별 보기", "일자별 보기"], horizontal=True)

  if search_mode == "월별 보기":
    months_list = sorted(history_df["년월"].unique(), reverse=True)
    selected_month = st.selectbox("조회할 월 선택", months_list)
    filtered_df = history_df[history_df["년월"] == selected_month]
  else:
    dates_list = sorted(
        history_df["날짜"].dt.strftime("%Y-%m-%d").unique(), reverse=True
    )
    selected_date = st.selectbox("조회할 일자 선택", dates_list)
    filtered_df = history_df[
        history_df["날짜"].dt.strftime("%Y-%m-%d") == selected_date
    ]

  if not filtered_df.empty:
    f_summary = (
        filtered_df.groupby("판매처")
        .agg(
            판매건수=("매출액", "count"),
            총매출액=("매출액", "sum"),
            총원가=("원가", "sum"),
            총배송비=("배송비", "sum"),
            총수수료=("수수료", "sum"),
            총순이익=("순이익", "sum"),
        )
        .reset_index()
    )

    f_summary["이익률(%)"] = f_summary.apply(
        lambda row: (row["총순이익"] / row["총매출액"] * 100)
        if row["총매출액"] > 0
        else 0.0,
        axis=1,
    )

    disp_sum = f_summary.copy()
    disp_sum["총매출액"] = disp_sum["총매출_액"].apply(
        lambda x: f"{int(x):,}원"
    ) if "총매출_액" in disp_sum.columns else disp_sum["총매출액"].apply(lambda x: f"{int(x):,}원")
    disp_sum["총원가"] = disp_sum["총원가"].apply(lambda x: f"{int(x):,}원")
    disp_sum["총배송비"] = disp_sum["총배송비"].apply(lambda x: f"{int(x):,}원")
    disp_sum["총수수료"] = disp_sum["총수수료"].apply(lambda x: f"{int(x):,}원")
    disp_sum["총순이익"] = disp_sum["총순이익"].apply(lambda x: f"{int(x):,}원")
    disp_sum["이익률(%)"] = disp_sum["이익률(%)"].apply(lambda x: f"{x:.2f}%")

    st.dataframe(disp_sum, use_container_width=True)
  else:
    st.info("선택한 조건에 해당하는 데이터가 없습니다.")

else:
  st.info("💡 아직 누적된 데이터가 없습니다. 상단에서 주문 엑셀 파일을 업로드해 주세요.")
