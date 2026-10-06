from datetime import datetime
import io
import zipfile
import pandas as pd
import streamlit as st

# ?섏씠吏 ?ㅼ젙
st.set_page_config(
    page_title="留덉폆吏???듯빀 ?먮ℓ愿由??꾨줈洹몃옩", page_icon="?벀", layout="centered"
)

# 1. ?몄뀡 ?곹깭 珥덇린??(?꾩쟻 ?곗씠??諛??ш퀬/?곹뭹 留덉뒪??愿由?
if "accumulated_sales" not in st.session_state:
  st.session_state["accumulated_sales"] = pd.DataFrame()
if "accumulated_garam" not in st.session_state:
  st.session_state["accumulated_garam"] = pd.DataFrame()
if "accumulated_kistic" not in st.session_state:
  st.session_state["accumulated_kistic"] = pd.DataFrame()
if "accumulated_frozen" not in st.session_state:
  st.session_state["accumulated_frozen"] = pd.DataFrame()

# 珥덇린 ?ш퀬 ?ㅼ젙
if "inventory" not in st.session_state:
  st.session_state["inventory"] = {
      "?ㅼ뒪??15g x 40媛?: 500,
      "?ㅼ뒪??15g x 100媛?: 500,
      "??諛붿궘??以묓솕 怨좎텛?≪콈 援곕쭔??1.2kg": 300,
      "源留먯씠?源400g": 400,
      "?ㅻ━吏??遺?곗뼱臾듬컮 80g x 10媛?: 300,
      "留ㅼ숴?ъ숴 遺?곗뼱臾듬컮 80g x 10媛?: 300,
      "?ㅼ쭠?댁빞梨?遺?곗뼱臾듬컮 80g x 10媛?: 300,
      "泥대떎移섏쫰 遺?곗뼱臾듬컮 80g x 10媛?: 300,
  }

# ?썱截??곹뭹 留덉뒪??愿由?(?먮ℓ媛, ?먭?, 諛곗넚鍮? 遺媛?몃퀎???щ? ?ㅼ젙)
if "product_master" not in st.session_state:
  st.session_state["product_master"] = {
      "?ㅼ뒪??15g x 40媛?: {
          "selling_price": 9900,
          "cost_price": 113 * 40,
          "shipping_fee": 2900,
          "vat_separate": False,
      },
      "?ㅼ뒪??15g x 100媛?: {
          "selling_price": 19900,
          "cost_price": 113 * 100,
          "shipping_fee": 2900,
          "vat_separate": False,
      },
      "??諛붿궘??以묓솕 怨좎텛?≪콈 援곕쭔??1.2kg": {
          "selling_price": 13900,
          "cost_price": 4700,
          "shipping_fee": 3900,
          "vat_separate": False,
      },
      "源留먯씠?源400g": {
          "selling_price": 13900,
          "cost_price": 1700 * 3,
          "shipping_fee": 3900,
          "vat_separate": False,
      },
      "?ㅻ━吏??遺?곗뼱臾듬컮 80g x 10媛?: {
          "selling_price": 18900,
          "cost_price": int(536 * 1.1 * 10),
          "shipping_fee": 4300,
          "vat_separate": True,
      },
      "留ㅼ숴?ъ숴 遺?곗뼱臾듬컮 80g x 10媛?: {
          "selling_price": 19900,
          "cost_price": int(560 * 1.1 * 10),
          "shipping_fee": 4300,
          "vat_separate": True,
      },
      "?ㅼ쭠?댁빞梨?遺?곗뼱臾듬컮 80g x 10媛?: {
          "selling_price": 20900,
          "cost_price": int(575 * 1.1 * 10),
          "shipping_fee": 4300,
          "vat_separate": True,
      },
      "泥대떎移섏쫰 遺?곗뼱臾듬컮 80g x 10媛?: {
          "selling_price": 21900,
          "cost_price": int(646 * 1.1 * 10),
          "shipping_fee": 4300,
          "vat_separate": True,
      },
  }

st.title("?벀 留덉폆吏???먮ℓ 諛??ш퀬 愿由??꾨줈洹몃옩")
st.write(
    "諛쒖＜???낅줈?????뚯씪 ???좎쭨 湲곗? 以묐났 寃利? ?ㅼ떆媛??ш퀬 李④컧, ?뚮옯??
    " ?섏닔猷?諛??깅줉???곹뭹 湲곗? ?쒖닔?듭씠 ?먮룞 ?뺤궛?⑸땲??"
)

# ?숋툘 ?뚮옯???섏닔猷뚯쑉 ?ㅼ젙
with st.expander("?숋툘 ?뚮옯???섏닔猷뚯쑉 ?곸꽭 ?ㅼ젙 (?대┃?섏뿬 ?닿린)", expanded=False):
  col_f1, col_f2, col_f3, col_f4, col_f5, col_f6 = st.columns(6)
  with col_f1:
    fee_smart = st.number_input(
        "?ㅻ쭏?몄뒪?좎뼱", value=5.80, step=0.1, format="%.2f"
    )
  with col_f2:
    fee_always = st.number_input("?ъ썾?댁쫰", value=5.50, step=0.1, format="%.2f")
  with col_f3:
    fee_coupang = st.number_input("荑좏뙜", value=10.80, step=0.1, format="%.2f")
  with col_f4:
    fee_gmarket = st.number_input("吏留덉폆", value=13.00, step=0.1, format="%.2f")
  with col_f5:
    fee_auction = st.number_input("?μ뀡", value=13.00, step=0.1, format="%.2f")
  with col_f6:
    fee_kakao = st.number_input(
        "移댁뭅?ㅼ눥?묓븯湲?, value=10.00, step=0.1, format="%.2f"
    )

fee_rates = {
    "?ㅻ쭏?몄뒪?좎뼱": fee_smart / 100.0,
    "?ㅼ씠踰?: fee_smart / 100.0,
    "?ъ썾?댁쫰": fee_always / 100.0,
    "荑좏뙜": fee_coupang / 100.0,
    "吏留덉폆": fee_gmarket / 100.0,
    "G留덉폆": fee_gmarket / 100.0,
    "?μ뀡": fee_auction / 100.0,
    "移댁뭅?ㅼ눥?묓븯湲?: fee_kakao / 100.0,
    "移댁뭅??: fee_kakao / 100.0,
}

st.markdown("---")

# --- [?곷떒 怨좎젙 ?꾩쟻 留ㅼ텧 諛??쒖닔????쒕낫?? ---
st.subheader("?뱤 [?꾩쟻 ?곗씠?? ?꾩껜 留ㅼ텧 諛??쒖닔???붿빟 ??쒕낫??)

acc_sales = st.session_state["accumulated_sales"]

if not acc_sales.empty:
  total_orders = len(acc_sales)
  total_revenue = acc_sales["?먮ℓ媛"].sum()
  total_cost = acc_sales["?먭?"].sum()
  total_shipping = acc_sales["諛곗넚鍮?].sum()
  total_platform_fee = acc_sales["?뚮옯?쇱닔?섎즺"].sum()
  total_net_profit = acc_sales["?쒖닔??].sum()

  m1, m2, m3, m4 = st.columns(4)
  m1.metric("?꾩쟻 珥?二쇰Ц 嫄댁닔", f"{total_orders:,} 嫄?)
  m2.metric("?꾩쟻 珥??먮ℓ 留ㅼ텧??, f"{total_revenue:,.0f} ??)
  m3.metric(
      "?먭?+諛곗넚+?섏닔猷??⑷퀎",
      f"{(total_cost + total_shipping + total_platform_fee):,.0f} ??,
  )
  m4.metric(
      "?꾩쟻 珥??쒖닔??,
      f"{total_net_profit:,.0f} ??,
      delta=(
          f"留덉쭊??{(total_net_profit/total_revenue*100):.1f}%"
          if total_revenue > 0
          else "0%"
      ),
  )

  with st.expander("?썟 ?뚮옯?쇰퀎 諛??쇱옄蹂??곸꽭 ?댁뿭 蹂닿린"):
    target_platforms = [
        "?ㅻ쭏?몄뒪?좎뼱",
        "?μ뀡",
        "吏留덉폆",
        "?ъ썾?댁쫰",
        "荑좏뙜",
        "移댁뭅?ㅼ눥?묓븯湲?,
    ]
    st.markdown("##### ?뚮옯?쇰퀎 ?꾩쟻 ?꾪솴")
    platform_summary = (
        acc_sales.groupby("?먮ℓ泥?)
        .agg(
            二쇰Ц嫄댁닔=("?먮ℓ媛", "count"),
            珥앺뙋留ㅺ?=("?먮ℓ媛", "sum"),
            珥앹썝媛=("?먭?", "sum"),
            珥앸같?〓퉬=("諛곗넚鍮?, "sum"),
            ?뚮옯?쇱닔?섎즺?⑷퀎=("?뚮옯?쇱닔?섎즺", "sum"),
            珥앹닚?섏씡=("?쒖닔??, "sum"),
        )
        .reindex(target_platforms)
        .fillna(0)
        .reset_index()
    )
    st.dataframe(platform_summary, use_container_width=True)

    st.markdown("##### ?낅줈???쇱옄蹂??꾩쟻 ?꾪솴")
    date_summary = (
        acc_sales.groupby("?낅줈?쒖씪??)
        .agg(
            二쇰Ц嫄댁닔=("?먮ℓ媛", "count"),
            留ㅼ텧??("?먮ℓ媛", "sum"),
            ?쒖닔??("?쒖닔??, "sum"),
        )
        .reset_index()
    )
    st.dataframe(date_summary, use_container_width=True)
else:
  st.info(
      "?꾩쭅 ?낅줈??諛?諛섏쁺???곗씠?곌? ?놁뒿?덈떎. ?꾨옒?먯꽌 諛쒖＜???뚯씪???낅줈?쒗빐"
      " 二쇱꽭??"
  )

st.markdown("---")

# --- [?곹뭹 留덉뒪??諛??ш퀬 愿由??뱀뀡] ---
tab_inv, tab_prod = st.tabs(["?벀 ?ㅼ떆媛??ш퀬 愿由?, "?뤇截??곹뭹 留덉뒪??愿由?(?좉퇋 ?깅줉)"])

with tab_inv:
  st.write("?꾩옱 李쎄퀬???⑥븘 ?덈뒗 ?곹뭹蹂??ㅼ떆媛??ш퀬 ?꾪솴?낅땲??")
  inv_df = pd.DataFrame(
      list(st.session_state["inventory"].items()),
      columns=["?곹뭹紐?, "?꾩옱怨좎닔??],
  )
  st.dataframe(inv_df, use_container_width=True)

  with st.form("inventory_form"):
    st.write("?뵩 ?ш퀬 ?섎룞 議곗젙")
    col_i1, col_i2, col_i3 = st.columns([3, 2, 1])
    with col_i1:
      selected_item = st.selectbox(
          "?곹뭹 ?좏깮", list(st.session_state["inventory"].keys())
      )
    with col_i2:
      add_qty = st.number_input(
          "?낃퀬/議곗젙 ?섎웾 (+/-)", value=0, step=1, format="%d"
      )
    with col_i3:
      submitted_inv = st.form_submit_button("?ш퀬 諛섏쁺")
    if submitted_inv and add_qty != 0:
      st.session_state["inventory"][selected_item] += add_qty
      st.success(f"{selected_item} ?ш퀬媛 ?깃났?곸쑝濡?諛섏쁺?섏뿀?듬땲??")
      st.rerun()

with tab_prod:
  st.write(
      "?깅줉???곹뭹?ㅼ쓽 ?먮ℓ媛, ?먭?, 諛곗넚鍮?湲곗????뺤씤?섍굅???덈줈???곹뭹??
      " 異붽??????덉뒿?덈떎."
  )
  prod_list = []
  for p_name, p_info in st.session_state["product_master"].items():
    prod_list.append({
        "?곹뭹紐?: p_name,
        "?먮ℓ媛": p_info["selling_price"],
        "?먭?": p_info["cost_price"],
        "諛곗넚鍮?: p_info["shipping_fee"],
        "遺媛?몃퀎?꾩뿬遺": "蹂꾨룄(10%媛??"
        if p_info["vat_separate"]
        else "?ы븿",
    })
  st.dataframe(pd.DataFrame(prod_list), use_container_width=True)

  with st.form("new_product_form"):
    st.write("???좎긽???깅줉 / 湲곗〈 ?곹뭹 ?섏젙")
    cp1, cp2, cp3 = st.columns(3)
    with cp1:
      new_p_name = st.text_input("?곹뭹紐?(?듭뀡 ?ы븿 ?뺥솗???낅젰)")
      new_s_price = st.number_input("?먮ℓ媛 (??", value=10000, step=100)
    with cp2:
      new_c_price = st.number_input("?먭? (??", value=5000, step=100)
      new_ship = st.number_input("諛곗넚鍮?(??", value=3000, step=100)
    with cp3:
      new_vat = st.checkbox("遺媛??蹂꾨룄 (怨듦툒媛??10% 異붽? 怨꾩궛)")
      new_inv_qty = st.number_input("珥덇린 ?ш퀬 ?섎웾", value=100, step=10)

    submitted_prod = st.form_submit_button("?곹뭹 ?깅줉/??ν븯湲?)
    if submitted_prod and new_p_name:
      st.session_state["product_master"][new_p_name] = {
          "selling_price": new_s_price,
          "cost_price": new_c_price,
          "shipping_fee": new_ship,
          "vat_separate": new_vat,
      }
      if new_p_name not in st.session_state["inventory"]:
        st.session_state["inventory"][new_p_name] = new_inv_qty
      st.success(f"'{new_p_name}' ?곹뭹???깃났?곸쑝濡??깅줉?섏뿀?듬땲??")
      st.rerun()

st.markdown("---")

# 1. ?뚯씪 ?낅줈???뱀뀡
st.subheader("1. 諛쒖＜???뚯씪 ?낅줈??)
col1, col2 = st.columns(2)

with col1:
  shopmoa_file = st.file_uploader(
      "?듬え??/ ?듯빀 諛쒖＜???뚯씪 (.xlsx)", type=["xlsx", "xls"], key="shopmoa"
  )

with col2:
  always_file = st.file_uploader(
      "?ъ썾?댁쫰 諛쒖＜???뚯씪 (.xlsx)", type=["xlsx", "xls"], key="always"
  )


def calculate_item_finance(product_name, option_name, channel):
  p_str = str(product_name)
  o_str = str(option_name)
  combined_text = p_str + " " + o_str

  matched_key = "湲고??곹뭹"
  for key in st.session_state["product_master"].keys():
    # ?ㅼ썙??留ㅼ묶 (?? ?ㅼ뒪?? 留뚮몢, 源留먯씠, ?대У諛??몃???ぉ)
    keywords = key.split()
    if all(kw in combined_text for kw in keywords[:2]):
      matched_key = key
      break
    elif "?ㅼ뒪?? in combined_text and "?ㅼ뒪?? in key:
      if "40媛? in combined_text and "40媛? in key:
        matched_key = key
        break
      elif "100媛? in combined_text and "100媛? in key:
        matched_key = key
        break
    elif "留뚮몢" in combined_text or "怨좎텛?≪콈" in combined_text:
      if "留뚮몢" in key or "怨좎텛?≪콈" in key:
        matched_key = key
        break
    elif "源留먯씠" in combined_text and "源留먯씠" in key:
      matched_key = key
      break
    elif "?대У諛? in combined_text and "?대У諛? in key:
      if "留ㅼ숴" in combined_text and "留ㅼ숴" in key:
        matched_key = key
        break
      elif "?ㅼ쭠?? in combined_text and "?ㅼ쭠?? in key:
        matched_key = key
        break
      elif "泥대떎" in combined_text and "泥대떎" in key:
        matched_key = key
        break
      elif "?ㅻ━吏?? in combined_text and "?ㅻ━吏?? in key:
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
    item_category = "湲고??곹뭹"

  rate = fee_rates.get(channel, 0.10)
  platform_fee = selling_price * rate
  net_profit = selling_price - platform_fee - cost_price - shipping_fee

  return {
      "移댄뀒怨좊━": item_category,
      "?먮ℓ媛": selling_price,
      "?먭?": cost_price,
      "諛곗넚鍮?: shipping_fee,
      "?뚮옯?쇱닔?섎즺": platform_fee,
      "?쒖닔??: net_profit,
  }


def get_column_value(row, possible_cols, default=""):
  for col in possible_cols:
    if col in row and pd.notna(row[col]):
      return str(row[col])
  return default


def extract_order_date(df):
  """?묒? ?뚯씪 ?댁뿉???좎쭨 ?뺥깭(YYYY-MM-DD ?먮뒗 YYYYMMDD)瑜??먯깋"""
  for col in df.columns:
    for val in df[col].dropna().astype(str):
      val_clean = val.strip()
      # ?좎쭨 ?⑦꽩 ?먯깋 ?쒕룄 (?? 2026-09-21 ?먮뒗 26-09-21 ??
      if (
          len(val_clean) >= 8
          and ("-" in val_clean or val_clean.isdigit())
          and ("202" in val_clean or "26" in val_clean)
      ):
        # YYYY-MM-DD ?뺥깭濡??뺢퇋???쒕룄
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

  # ?낅줈?쒕맂 ?뚯씪?ㅼ뿉???좎쭨 異붿텧 (?곗꽑 ?쒖쐞: ?듬え??-> ?ъ썾?댁쫰 -> ?ㅻ뒛?좎쭨)
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

      if "荑좏뙜" in row_str:
        detected_channel = "荑좏뙜"
      elif "?ㅻ쭏?몄뒪?좎뼱" in row_str or "?ㅼ씠踰? in row_str:
        detected_channel = "?ㅻ쭏?몄뒪?좎뼱"
      elif "吏留덉폆" in row_str or "G留덉폆" in row_str:
        detected_channel = "吏留덉폆"
      elif "?μ뀡" in row_str:
        detected_channel = "?μ뀡"
      elif "移댁뭅?? in row_str or "?쇳븨?섍린" in row_str:
        detected_channel = "移댁뭅?ㅼ눥?묓븯湲?
      elif "?ъ썾?댁쫰" in row_str:
        detected_channel = "?ъ썾?댁쫰"

      if default_channel_name == "?듬え??:
        sname = get_column_value(row, ["?섏랬?몃챸", "?섎졊??, "諛쏅뒗遺꾩꽦紐?])
        phone = get_column_value(
            row, ["?섏랬???꾪솕踰덊샇", "?섎졊???곕씫泥?, "?꾪솕踰덊샇"]
        )
        mobile = get_column_value(
            row, ["?섏랬???몃뱶?곕쾲??, "?섎졊???몃뱶??, "?대??곕쾲??, "?몃뱶??]
        )
        if not mobile:
          mobile = phone
        zipcode = get_column_value(row, ["?고렪踰덊샇"])
        address = get_column_value(row, ["?섏랬?몄＜??, "二쇱냼"])
        p_name = get_column_value(row, ["?곹뭹紐?])
        opt_name = get_column_value(row, ["?듭뀡", "?곹뭹?듭뀡"])
        qty_val = get_column_value(row, ["?섎웾", "二쇰Ц?섎웾"], "1")
        qty = int(pd.to_numeric(qty_val, errors="coerce") or 1)
        msg = get_column_value(row, ["諛곗넚硫붿꽭吏", "諛곗넚硫붾え", "怨좉컼?붿껌?ы빆"])
        order_id = get_column_value(row, ["二쇰Ц踰덊샇", "二쇰Ц?꾩씠??])
        invoice_no = get_column_value(
            row, ["?≪옣踰덊샇", "?앸같?≪옣踰덊샇", "?댁넚?λ쾲??]
        )
      else:
        sname = get_column_value(row, ["?섎졊??, "?섏랬?몃챸"])
        phone = get_column_value(row, ["?섎졊???곕씫泥?, "?꾪솕踰덊샇"])
        mobile = get_column_value(row, ["?섎졊???몃뱶??, "?몃뱶??, "?대??곕쾲??])
        if not mobile:
          mobile = phone
        zipcode = get_column_value(row, ["?고렪踰덊샇"])
        address = get_column_value(row, ["二쇱냼", "?섏랬?몄＜??])
        p_name = get_column_value(row, ["?곹뭹紐?])
        opt_name = get_column_value(row, ["?듭뀡", "?곹뭹?듭뀡"])
        qty_val = get_column_value(row, ["?섎웾", "二쇰Ц?섎웾"], "1")
        qty = int(pd.to_numeric(qty_val, errors="coerce") or 1)
        msg = get_column_value(row, ["諛곗넚硫붾え", "諛곗넚硫붿꽭吏"])
        order_id = get_column_value(row, ["二쇰Ц?꾩씠??, "二쇰Ц踰덊샇"])
        invoice_no = get_column_value(
            row, ["?≪옣踰덊샇", "?앸같?≪옣踰덊샇", "?댁넚?λ쾲??]
        )

      fin = calculate_item_finance(p_name, opt_name, detected_channel)

      for _ in range(max(1, qty)):
        sales_data_list.append({
            "?낅줈?쒖씪??: detected_date,
            "?먮ℓ泥?: detected_channel,
            "二쇰Ц踰덊샇": str(order_id),
            "?곹뭹紐?: fin["移댄뀒怨좊━"],
            "?먮ℓ媛": fin["?먮ℓ媛"],
            "?먭?": fin["?먭?"],
            "諛곗넚鍮?: fin["諛곗넚鍮?],
            "?뚮옯?쇱닔?섎즺": fin["?뚮옯?쇱닔?섎즺"],
            "?쒖닔??: fin["?쒖닔??],
        })

      base_row = {
          "?먭꺽_諛쏅뒗遺꾩꽦紐?: sname,
          "?먭꺽_諛쏅뒗遺꾩쟾?붾쾲??: phone,
          "?먭꺽_諛쏅뒗遺꾧린??곕씫泥?: mobile,
          "?먭꺽_諛쏅뒗遺꾩슦?몃쾲??: zipcode,
          "?먭꺽_諛쏅뒗遺꾩＜??: address,
          "?곹뭹紐??먮낯": p_name,
          "?듭뀡_?먮낯": opt_name,
          "?곹뭹?섎웾": qty,
          "諛곗넚硫붿꽭吏1": msg,
          "二쇰Ц踰덊샇": order_id,
          "?≪옣踰덊샇": invoice_no,
          "二쇰Ц??: detected_date,
          "?먮ℓ泥?: detected_channel,
      }
      frames.append(base_row)

  parse_dataframe(shopmoa_df, "?듬え??)
  parse_dataframe(always_df, "?ъ썾?댁쫰")

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
    p_name = str(row["?곹뭹紐??먮낯"])
    opt_name = str(row["?듭뀡_?먮낯"])
    qty = int(row["?곹뭹?섎웾"])

    def create_garam_row(name, quantity):
      return {
          "諛쏅뒗遺꾩꽦紐?: name,
          "諛쏅뒗遺꾩쟾?붾쾲??: row["?먭꺽_諛쏅뒗遺꾩쟾?붾쾲??],
          "諛쏅뒗遺꾧린??곕씫泥?: row["?먭꺽_諛쏅뒗遺꾧린??곕씫泥?],
          "諛쏅뒗遺꾩슦?몃쾲??: row["?먭꺽_諛쏅뒗遺꾩슦?몃쾲??],
          "諛쏅뒗遺꾩＜??: row["?먭꺽_諛쏅뒗遺꾩＜??],
          "?댄뭹?섎웾": quantity,
          "諛곗넚硫붿꽭吏1": row["諛곗넚硫붿꽭吏1"],
          "異쒕젰??: "",
          "?댁엫援щ텇": "",
          "湲곕낯?댁엫": "",
          "怨좉컼?ъ슜踰덊샇": "",
          "?덈챸": "",
          "?먮ℓ泥?: row["?먮ℓ泥?],
          "二쇰Ц踰덊샇": row["二쇰Ц踰덊샇"],
          "?≪옣踰덊샇": row["?≪옣踰덊샇"],
          "二쇰Ц??: row["二쇰Ц??],
          "?먮ℓ媛": "",
          "?뺤궛湲덉븸": "",
          "嫄곕옒泥섏퐫??: 16,
      }

    def create_standard_row(name, quantity):
      return {
          "?섎졊?먯씠由?: name,
          "?섎졊?먯쟾??: row["?먭꺽_諛쏅뒗遺꾩쟾?붾쾲??],
          "?섎졊?먰쑕???: row["?먭꺽_諛쏅뒗遺꾧린??곕씫泥?],
          "?섎졊?먯슦?몃쾲??: row["?먭꺽_諛쏅뒗遺꾩슦?몃쾲??],
          "?섎졊?먯＜??: row["?먭꺽_諛쏅뒗遺꾩＜??],
          "?곹뭹?섎웾": quantity,
          "諛곗넚硫붾え": row["諛곗넚硫붿꽭吏1"],
          "?쒖“??: "",
          "移댄뀒怨좊━": "",
          "?덉젅": "",
          "諛곗넚 蹂대쪟": "",
          "?곹뭹紐?: "",
          "?먮ℓ泥?: row["?먮ℓ泥?],
          "二쇰Ц踰덊샇": row["二쇰Ц踰덊샇"],
          "諛쒖＜??: "",
          "愿由щ쾲??: "",
          "?곹깭": "",
          "?≪옣踰덊샇": row["?≪옣踰덊샇"],
      }

    # ?대У諛?遺꾧린 (媛?뚯떇??
    if "?대У諛? in p_name or "?대У諛? in opt_name:
      target_name = "?ㅻ━吏??遺?곗뼱臾듬컮 80g x 10媛?
      if "留ㅼ숴?ъ숴" in opt_name or "留ㅼ숴?쒕쭧" in p_name:
        target_name = "留ㅼ숴?ъ숴 遺?곗뼱臾듬컮 80g x 10媛?
      elif "?ㅼ쭠?댁빞梨? in opt_name or "?ㅼ쭠?댁빞梨? in p_name:
        target_name = "?ㅼ쭠?댁빞梨?遺?곗뼱臾듬컮 80g x 10媛?
      elif "泥대떎移섏쫰" in opt_name or "泥대떎移섏쫰" in p_name:
        target_name = "泥대떎移섏쫰 遺?곗뼱臾듬컮 80g x 10媛?

      base_name = str(row["?먭꺽_諛쏅뒗遺꾩꽦紐?])
      for i in range(qty):
        r_name = f"{base_name}{i+1}" if qty > 1 else base_name
        r_copy = create_garam_row(r_name, 1)
        r_copy["?덈챸"] = target_name
        garam_rows.append(r_copy)
        if target_name in st.session_state["inventory"]:
          st.session_state["inventory"][target_name] -= 1

    # ?ㅼ뒪??遺꾧린
    elif "?ㅼ뒪?? in p_name or "?ㅼ뒪?? in opt_name:
      is_40 = "40媛? in p_name or "40媛? in opt_name
      base_name = str(row["?먭꺽_諛쏅뒗遺꾩꽦紐?])

      if is_40:
        if qty == 2:
          r_copy = create_standard_row(base_name, 1)
          r_copy["?곹뭹紐?] = "?ㅼ뒪??15g x 100媛?
          kistic_rows.append(r_copy)
          if "?ㅼ뒪??15g x 100媛? in st.session_state["inventory"]:
            st.session_state["inventory"]["?ㅼ뒪??15g x 100媛?] -= 1
        elif qty == 3:
          r1 = create_standard_row(base_name, 1)
          r1["?곹뭹紐?] = "?ㅼ뒪??15g x 40媛?
          kistic_rows.append(r1)
          r2 = create_standard_row(f"{base_name}2", 1)
          r2["?곹뭹紐?] = "?ㅼ뒪??15g x 100媛?
          kistic_rows.append(r2)
          if "?ㅼ뒪??15g x 40媛? in st.session_state["inventory"]:
            st.session_state["inventory"]["?ㅼ뒪??15g x 40媛?] -= 1
          if "?ㅼ뒪??15g x 100媛? in st.session_state["inventory"]:
            st.session_state["inventory"]["?ㅼ뒪??15g x 100媛?] -= 1
        else:
          r_copy = create_standard_row(base_name, qty)
          r_copy["?곹뭹紐?] = "?ㅼ뒪??15g x 40媛?
          kistic_rows.append(r_copy)
          if "?ㅼ뒪??15g x 40媛? in st.session_state["inventory"]:
            st.session_state["inventory"]["?ㅼ뒪??15g x 40媛?] -= qty
      else:
        r_copy = create_standard_row(base_name, qty)
        r_copy["?곹뭹紐?] = "?ㅼ뒪??15g x 100媛?
        kistic_rows.append(r_copy)
        if "?ㅼ뒪??15g x 100媛? in st.session_state["inventory"]:
          st.session_state["inventory"]["?ㅼ뒪??15g x 100媛?] -= qty

    # 留뚮몢 遺꾧린
    elif "留뚮몢" in p_name or "怨좎텛?≪콈" in p_name:
      base_name = str(row["?먭꺽_諛쏅뒗遺꾩꽦紐?])
      r_copy = create_standard_row(base_name, qty)
      r_copy["?곹뭹紐?] = "??諛붿궘??以묓솕 怨좎텛?≪콈 援곕쭔??1.2kg"
      frozen_rows.append(r_copy)
      if "??諛붿궘??以묓솕 怨좎텛?≪콈 援곕쭔??1.2kg" in st.session_state["inventory"]:
        st.session_state["inventory"][
            "??諛붿궘??以묓솕 怨좎텛?≪콈 援곕쭔??1.2kg"
        ] -= qty

    # 源留먯씠 遺꾧린
    elif "源留먯씠" in p_name:
      base_name = str(row["?먭꺽_諛쏅뒗遺꾩꽦紐?])
      r_copy = create_standard_row(base_name, qty * 3)
      r_copy["?곹뭹紐?] = "源留먯씠?源400g"
      frozen_rows.append(r_copy)
      if "源留먯씠?源400g" in st.session_state["inventory"]:
        st.session_state["inventory"]["源留먯씠?源400g"] -= qty * 3

  garam_cols = [
      "諛쏅뒗遺꾩꽦紐?,
      "諛쏅뒗遺꾩쟾?붾쾲??,
      "諛쏅뒗遺꾧린??곕씫泥?,
      "諛쏅뒗遺꾩슦?몃쾲??,
      "諛쏅뒗遺꾩＜??,
      "?댄뭹?섎웾",
      "諛곗넚硫붿꽭吏1",
      "異쒕젰??,
      "?댁엫援щ텇",
      "湲곕낯?댁엫",
      "怨좉컼?ъ슜踰덊샇",
      "?덈챸",
      "?먮ℓ泥?,
      "二쇰Ц踰덊샇",
      "?≪옣踰덊샇",
      "二쇰Ц??,
      "?먮ℓ媛",
      "?뺤궛湲덉븸",
      "嫄곕옒泥섏퐫??,
  ]
  kistic_cols = [
      "?섎졊?먯씠由?,
      "?섎졊?먯쟾??,
      "?섎졊?먰쑕???,
      "?섎졊?먯슦?몃쾲??,
      "?섎졊?먯＜??,
      "?곹뭹?섎웾",
      "諛곗넚硫붾え",
      "?쒖“??,
      "移댄뀒怨좊━",
      "?덉젅",
      "諛곗넚 蹂대쪟",
      "?곹뭹紐?,
      "?먮ℓ泥?,
      "二쇰Ц踰덊샇",
      "諛쒖＜??,
      "愿由щ쾲??,
      "?곹깭",
      "?≪옣踰덊샇",
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


# 2. ?ㅽ뻾 諛??ㅼ슫濡쒕뱶 踰꾪듉 ?뱀뀡
st.markdown("---")
st.subheader("2. 留욎땄??諛쒖＜??蹂??諛??꾩쟻 ?곗씠??諛섏쁺 ?ㅽ뻾")

col_btn1, col_btn2, col_btn3 = st.columns([2, 2, 1])

with col_btn1:
  run_clicked = st.button(
      "?? 諛쒖＜??蹂??諛??ш퀬李④컧/?꾩쟻 諛섏쁺", type="primary"
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
          f"媛?뚯떇???듯빀?꾩쟻_諛쒖＜??{current_date_str}.xlsx", g_io.getvalue()
      )

    if not st.session_state["accumulated_kistic"].empty:
      k_io = io.BytesIO()
      with pd.ExcelWriter(k_io, engine="openpyxl") as writer:
        st.session_state["accumulated_kistic"].to_excel(writer, index=False)
      zip_file.writestr(
          f"?ㅼ뒪???듯빀?꾩쟻_諛쒖＜??{current_date_str}.xlsx", k_io.getvalue()
      )

    if not st.session_state["accumulated_frozen"].empty:
      f_io = io.BytesIO()
      with pd.ExcelWriter(f_io, engine="openpyxl") as writer:
        st.session_state["accumulated_frozen"].to_excel(writer, index=False)
      zip_file.writestr(
          f"?됰룞?앺뭹_?듯빀?꾩쟻_諛쒖＜??{current_date_str}.xlsx", f_io.getvalue()
      )
  zip_buffer.seek(0)

  st.download_button(
      label="?뱿 ?꾩쟻 ?듯빀 諛쒖＜??ZIP ?ㅼ슫濡쒕뱶",
      data=zip_buffer,
      file_name=f"留덉폆吏???꾩껜?꾩쟻_?듯빀諛쒖＜??{current_date_str}.zip",
      mime="application/zip",
  )

with col_btn3:
  if st.button("?㏏ ?꾩껜 珥덇린??):
    st.session_state["accumulated_sales"] = pd.DataFrame()
    st.session_state["accumulated_garam"] = pd.DataFrame()
    st.session_state["accumulated_kistic"] = pd.DataFrame()
    st.session_state["accumulated_frozen"] = pd.DataFrame()
    st.success("珥덇린???꾨즺")
    st.rerun()

if run_clicked:
  if shopmoa_file is None and always_file is None:
    st.warning("理쒖냼 ??媛??댁긽??諛쒖＜???뚯씪???낅줈?쒗빐 二쇱꽭??")
  else:
    try:
      s_df = pd.read_excel(shopmoa_file) if shopmoa_file else None
      a_df = pd.read_excel(always_file) if always_file else None

      # 1李??뚯떛?섏뿬 ?뚯씪 ???좎쭨 癒쇱? 媛먯?
      _, _, _, _, detected_date = process_custom_orders(s_df, a_df)

      # 以묐났 ?낅줈??寃利?(?대? ?대떦 ?좎쭨 ?곗씠?곌? ?꾩쟻 sales??議댁옱?섎뒗吏 ?뺤씤)
      existing_sales = st.session_state["accumulated_sales"]
      if not existing_sales.empty and detected_date in existing_sales[
          "?낅줈?쒖씪??
        ].astype(str).values:
        st.error(
            f"?좑툘 [以묐났 ?낅줈??諛⑹?] ?대? '{detected_date}' ?쇱옄??諛쒖＜???곗씠?곌?"
            " ?꾩쟻 諛섏쁺?섏뼱 ?덉뒿?덈떎. ?숈씪???뚯씪? 以묐났 ?곸슜?섏? ?딆뒿?덈떎."
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
            f"??[?좎쭨: {date_str}] 諛쒖＜?쒓? ?깃났?곸쑝濡?遺꾩꽍?섏뼱 ?ш퀬 李④컧 諛?
            " ?꾩쟻 諛섏쁺?섏뿀?듬땲??"
        )
        st.rerun()

    except Exception as e:
      st.error(f"?뚯씪 泥섎━ 以??ㅻ쪟媛 諛쒖깮?덉뒿?덈떎: {e}")
