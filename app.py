import datetime
import io
import os
import tempfile
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
    "**샵모아** 및 **올웨이즈** 주문 파일을 업로드하면, 플랫폼별(쿠팡, 스마트스토어,"
    " 11번가 등)로 매출·순이익을 자동 정산하고 발주서를 생성합니다!"
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
          "주문번호",
          "상품명",
          "수량",
          "매출액",
          "원가",
          "배송비",
          "수수료",
          "순이익",
      ]
  )


# 누적 데이터 저장 함수 (선택한 날짜 기준으로 중복 제거 후 저장)
def save_history_deduplicated(new_df, target_date):
  existing_df = load_history()
  if not existing_df.empty:
    existing_df["날짜"] = existing_df["날짜"].astype(str)
    other_dates_df = existing_df[existing_df["날짜"] != target_date]
    combined = pd.concat([other_dates_df, new_df], ignore_index=True)
    combined.to_csv(DB_FILE, index=False, encoding="utf-8-sig")
  else:
    new_df.to_csv(DB_FILE, index=False, encoding="utf-8-sig")


# 파일 업로드 섹션 (모바일 호환성 강화: type 제한 해제)
col_up1, col_up2 = st.columns(2)
with col_up1:
  st.subheader("🛒 샵모아 주문 파일")
  shopmoa_file = st.file_uploader(
      "샵모아 파일 업로드 (엑셀/CSV)", key="shop"
  )
with col_up2:
  st.subheader("🚀 올웨이즈 주문 파일")
  always_file = st.file_uploader(
      "올웨이즈 파일 업로드 (엑셀/CSV)", key="always"
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
    st.warning("주문 파일을 최소한 하나 이상 업로드해 주세요!")
  else:
    all_rows = []
    read_success = True

    try:
      # 1. 샵모아 파일 읽기 처리
      if shopmoa_file:
        file_name = shopmoa_file.name.lower()
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".csv" if "csv" in file_name else ".xlsx",
        ) as tmp_file:
          tmp_file.write(shopmoa_file.getvalue())
          tmp_path = tmp_file.name

        try:
          if "csv" in file_name:
            df_shop = pd.read_csv(tmp_path)
          else:
            try:
              df_shop = pd.read_excel(tmp_path)
            except Exception:
              df_shop = pd.read_csv(tmp_path)
        finally:
          if os.path.exists(tmp_path):
            os.remove(tmp_path)

        for _, row in df_shop.iterrows():
          # 엑셀 안에서 개별 플랫폼(쿠팡, 스마트스토어, 11번가 등) 인식
          site_name = "샵모아기타"
          for col in [
              "사이트",
              "판매처",
              "쇼핑몰",
              "마켓명",
              "판매채널",
              "주문매체",
          ]:
            if col in df_shop.columns and pd.notna(row.get(col)):
              val = str(row.get(col)).strip()
              if val:
                site_name = val
                break

          # 상품명과 옵션을 결합하여 정확한 판단 기준 확보
          p_name = str(row.get("상품명", ""))
          opt_name = (
              str(row.get("옵션명", "")) if "옵션명" in df_shop.columns else ""
          )
          combined_text = f"{p_name} {opt_name}"

          all_rows.append({
              "주문번호": str(
                  row.get(
                      "주문번호", row.get("주문 번호", row.get("주문아이디", ""))
                  )
              ),
              "판단기준텍스트": combined_text,
              "상품명": p_name,
              "수량": int(row.get("수량", 1))
              if pd.notna(row.get("수량"))
              else 1,
              "수취인명": str(
                  row.get(
                      "수취인명", row.get("수령인", row.get("받는분성명", ""))
                  )
              ),
              "전화번호": str(
                  row.get(
                      "수취인 전화번호",
                      row.get("수령인 연락처", row.get("전화번호", "")),
                  )
              ),
              "휴대폰번호": str(
                  row.get(
                      "수취인 핸드폰번호", row.get("휴대폰번호", "")
                  )
              ),
              "주소": str(
                  row.get(
                      "수취인주소", row.get("주소", row.get("받는분주소", ""))
                  )
              ),
              "우편번호": str(
                  row.get("우편번호", row.get("받는분우편번호", ""))
              ),
              "배송메모": str(
                  row.get(
                      "배송메세지",
                      row.get("배송메모", row.get("배송메세지1", "")),
                  )
              ),
              "판매처": site_name,
          })

      # 2. 올웨이즈 파일 읽기 처리 (옵션 기준 철저 분기)
      if always_file:
        file_name_alw = always_file.name.lower()
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".csv" if "csv" in file_name_alw else ".xlsx",
        ) as tmp_file:
          tmp_file.write(always_file.getvalue())
          tmp_path = tmp_file.name

        try:
          if "csv" in file_name_alw:
            df_alw = pd.read_csv(tmp_path)
          else:
            try:
              df_alw = pd.read_excel(tmp_path)
            except Exception:
              df_alw = pd.read_csv(tmp_path)
        finally:
          if os.path.exists(tmp_path):
            os.remove(tmp_path)

        for _, row in df_alw.iterrows():
          p_name = str(row.get("상품명", ""))
          opt_name = str(
              row.get("옵션", row.get("옵션명", row.get("상품옵션", "")))
          )
          combined_text = f"{p_name} {opt_name}"

          all_rows.append({
              "주문번호": str(
                  row.get(
                      "주문아이디", row.get("주문번호", row.get("주문 번호", ""))
                  )
              ),
              "판단기준텍스트": combined_text,  # 올웨이즈는 특히 옵션명이 핵심
              "상품명": p_name,
              "수량": int(row.get("수량", 1))
              if pd.notna(row.get("수량"))
              else 1,
              "수취인명": str(
                  row.get("수령인", row.get("수취인명", row.get("받는분", "")))
              ),
              "전화번호": str(
                  row.get("수령인 연락처", row.get("연락처", ""))
              ),
              "휴대폰번호": "",
              "주소": str(row.get("주소", row.get("수취인주소", ""))),
              "우편번호": str(row.get("우편번호", "")),
              "배송메모": str(
                  row.get(
                      "배송메모", row.get("배송메세지", row.get("고객요청사항", ""))
                  )
              ),
              "판매처": "올웨이즈",  # 올웨이즈 플랫폼 명시
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
        check_text = str(r["판단기준텍스트"])
        p_name = str(r["상품명"])
        orig_qty = int(r["수량"])
        base_name = str(r["수취인명"])
        platform = str(r["판매처"])
        order_num = str(r["주문번호"])

        # 1. 키스틱 상품 판별
        if "키스틱" in check_text or "기스틱" in check_text:
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
                "주문번호": order_num,
                "상품명": "키스틱 100개입",
                "수량": 1,
                "매출액": price_100,
                "원가": cost_100,
                "배송비": deliv_per_unit,
            })
            키스틱_rows.append({
                "수령자이름": base_name,
                "수령자전화": r["전화번호"],
                "수령자휴대폰": r["휴대폰번호"],
                "수령자우편번호": r["우편번호"],
                "수령자주소": r["주소"],
                1: 1,
                "배송메모": r["배송메모"],
                "상품명": "키스틱 15g x 100개",
                "주문번호": order_num,
            })

          for _ in range(rem_40):
            current_batch_financial.append({
                "날짜": order_date_str,
                "판매처": platform,
                "주문번호": order_num,
                "상품명": "키스틱 40개입",
                "수량": 1,
                "매출액": price_40,
                "원가": cost_40,
                "배송비": deliv_per_unit,
            })
            키스틱_rows.append({
                "수령자이름": base_name,
                "수령자전화": r["전화번호"],
                "수령자휴대폰": r["휴대폰번호"],
                "수령자우편번호": r["우편번호"],
                "수령자주소": r["주소"],
                1: 1,
                "배송메모": r["배송메모"],
                "상품명": "키스틱 15g x 40개",
                "주문번호": order_num,
            })

        # 2. 어묵바 상품 판별 (가람식품)
        elif "어묵" in check_text or "어묵바" in check_text:
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
                "주문번호": order_num,
                "상품명": norm_name,
                "수량": 1,
                "매출액": fixed_price,
                "원가": net_cost,
                "배송비": deliv_per_unit,
            })
            split_name = f"{base_name}{i}" if orig_qty > 1 else base_name
            가람식품_rows.append({
                "받는분성명": split_name,
                "받는분전화번호": r["전화번호"]
                if r["전화번호"]
                else r["휴대폰번호"],
                "받는분우편번호": r["우편번호"],
                "받는분주소": r["주소"],
                "내품수량": 1,
                "배송메세지1": r["배송메모"],
                "품명": norm_name,
                "주문번호": order_num,
            })

        # 3. 냉동 품목 판별 (고추잡채만두, 김말이 등)
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
                "주문번호": order_num,
                "상품명": norm_frozen_name,
                "수량": 1,
                "매출액": fixed_price,
                "원가": single_cost,
                "배송비": deliv_per_unit,
            })

          냉동_rows.append({
              "수령자이름": base_name,
              "수령자전화": r["전화번호"],
              "수령자휴대폰": r["휴대폰번호"],
              "수령자우편번호": r["우편번호"],
              "수령자주소": r["주소"],
              "상품수량": orig_qty,
              "배송메모": r["배송메모"],
              "상품명": norm_frozen_name,
              "주문번호": order_num,
          })

      # 재무 데이터 계산 및 중복 방지 저장
      df_current_batch = pd.DataFrame(current_batch_financial)
      if not df_current_batch.empty:

        def get_comm(row):
          p = str(row["판매처"])
          rev = row["매출액"]
          # 올웨이즈는 7%, 기타 플랫폼(쿠팡, 스마트스토어 등)은 5.5% 적용
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
        save_history_deduplicated(df_current_batch, order_date_str)

      st.success(
          f"✅ [{order_date_str}] 데이터 분석 및 플랫폼별 정산 반영 완료!"
      )

      # 송장(발주서) ZIP 파일 생성 다운로드 버튼 제공 (파일 이름에 날짜 포함)
      zip_buffer = io.BytesIO()
      with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        if 키스틱_rows:
          df_k = pd.DataFrame(키스틱_rows)
          csv_k = df_k.to_csv(index=False, encoding="utf-8-sig")
          zf.writestr(f"키스틱_발주서_{order_date_str}.csv", csv_k)
        if 가람식품_rows:
          df_g = pd.DataFrame(가람식품_rows)
          csv_g = df_g.to_csv(index=False, encoding="utf-8-sig")
          zf.writestr(f"가람식품_어묵바_발주서_{order_date_str}.csv", csv_g)
        if 냉동_rows:
          df_n = pd.DataFrame(냉동_rows)
          csv_n = df_n.to_csv(index=False, encoding="utf-8-sig")
          zf.writestr(f"냉동식품_발주서_{order_date_str}.csv", csv_n)

      zip_buffer.seek(0)
      st.download_button(
          label=f"📦 [{order_date_str}] 품목별 발주서 ZIP 다운로드",
          data=zip_buffer,
          file_name=f"발주서_{order_date_str}.zip",
          mime="application/zip",
      )

# ----------------------------------------------------
# 📊 상단 대시보드 및 플랫폼별 누적 데이터 조회 섹션
# ----------------------------------------------------
st.markdown("---")
st.header("📈 마켓지니 플랫폼별 종합 매출 & 순이익 대시보드")

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
  st.subheader("🔍 일자별 / 월별 플랫폼별 상세 현황")

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
    # 판매처(쿠팡, 스마트스토어, 올웨이즈 등)별 그룹화 집계
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
    disp_sum["총매출액"] = disp_sum["총매출액"].apply(lambda x: f"{int(x):,}원")
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
