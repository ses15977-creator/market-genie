import hashlib
import pandas as pd
import streamlit as st

# 1. 세션 상태 초기화 (누적 데이터를 저장할 공간)
if "uploaded_files_history" not in st.session_state:
  st.session_state.uploaded_files_history = set()  # 업로드된 파일 해시 저장용
if "accumulated_df" not in st.session_state:
  st.session_state.accumulated_df = pd.DataFrame()  # 전체 누적 데이터프레임

st.title("마켓지니 판매관리 프로그램")

# 파일 업로더 (여러 개 또는 단일 파일)
uploaded_files = st.file_uploader(
    "엑셀 또는 CSV 파일을 업로드하세요",
    type=["csv", "xlsx"],
    accept_multiple_files=True,
)

if uploaded_files:
  new_data_list = []

  for uploaded_file in uploaded_files:
    # 파일 고유 식별을 위한 해시값 생성 (중복 파일 감지용)
    file_bytes = uploaded_file.getvalue()
    file_hash = hashlib.md5(file_bytes).hexdigest()

    if file_hash in st.session_state.uploaded_files_history:
      st.warning(
          f"⚠️ 이미 업로드된 동일한 파일입니다. (파일명: {uploaded_file.name})"
      )
      continue

    # 파일 읽기 (CSV 또는 Excel)
    try:
      if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
      else:
        df = pd.read_excel(uploaded_file)

      # 파일 고유 해시 기록
      st.session_state.uploaded_files_history.add(file_hash)
      new_data_list.append(df)
      st.success(f"파일 업로드 성공: {uploaded_file.name}")

    except Exception as e:
      st.error(f"파일을 읽는 중 오류가 발생했습니다 ({uploaded_file.name}): {e}")

  # 새로운 유효 데이터가 있으면 기존 누적 데이터에 병합
  if new_data_list:
    new_df = pd.concat(new_data_list, ignore_index=True)

    # 기존 누적 데이터와 합치기
    if st.session_state.accumulated_df.empty:
      st.session_state.accumulated_df = new_df
    else:
      st.session_state.accumulated_df = pd.concat(
          [st.session_state.accumulated_df, new_df], ignore_index=True
      )

    # 데이터 내 날짜 컬럼을 기준으로 정렬 및 행 중복 제거 (주문번호 등이 있다면 기준 컬럼 지정 가능)
    # 예: 주문번호나 상세 내역 기준 중복 제거가 필요할 경우 아래 주석 해제
    # if '주문번호' in st.session_state.accumulated_df.columns:
    #     st.session_state.accumulated_df.drop_duplicates(subset=['주문번호'], keep='last', inplace=True)

    st.session_state.accumulated_df.drop_duplicates(inplace=True)

# 3. 누적 데이터 및 날짜별 요약 출력
if not st.session_state.accumulated_df.empty:
  st.subheader("📊 업로드 일자별 / 마켓별 누적 요약")

  df_acc = st.session_state.accumulated_df

  # 날짜 컬럼이 존재할 경우 날짜별 집계 예시
  # (실제 데이터프레임의 날짜 컬럼명에 맞게 '업로드일자' 또는 '주문일자'를 수정해주세요)
  date_col = (
      "업로드일자"
      if "업로드일자" in df_acc.columns
      else df_acc.columns[0]
  )

  # 예시 집계 (주문건수, 매출액, 순수익 등)
  # st.dataframe(df_acc)
