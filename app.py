import pandas as pd


def process_custom_orders(shopmoa_df, always_df):
    frames = []

    # 1. 샵모아 데이터 표준화
    if shopmoa_df is not None and not shopmoa_df.empty:
        s_df = shopmoa_df.copy()
        s_df["수령자이름"] = s_df.get("수취인명", "")
        s_df["수령자전화"] = s_df.get("수취인 전화번호", "")
        s_df["수령자휴대폰"] = s_df.get("수취인 핸드폰번호", "")
        s_df["수령자우편번호"] = s_df.get("우편번호", "")
        s_df["수령자주소"] = s_df.get("수취인주소", "")
        s_df["상품명_원본"] = s_df.get("상품명", "")
        s_df["옵션_원본"] = s_df.get("옵션", "")
        s_df["상품수량"] = s_df.get("수량", 1)
        s_df["배송메모"] = s_df.get("배송메세지", "")
        s_df["주문번호"] = s_df.get("주문번호", "")
        frames.append(s_df)

    # 2. 올웨이즈 데이터 표준화 (옵션명에서 상품명 추출)
    if always_df is not None and not always_df.empty:
        a_df = always_df.copy()
        a_df["수령자이름"] = a_df.get("수령인", "")
        a_df["수령자전화"] = a_df.get("수령인 연락처", "")
        a_df["수령자휴대폰"] = a_df.get("수령인 연락처", "")
        a_df["수령자우편번호"] = a_df.get("우편번호", "")
        a_df["수령자주소"] = a_df.get("주소", "")
        a_df["상품명_원본"] = a_df.get("상품명", "")
        a_df["옵션_원본"] = a_df.get("옵션", "")
        a_df["상품수량"] = a_df.get("수량", 1)
        a_df["배송메모"] = ""
        a_df["주문번호"] = a_df.get("주문아이디", "")
        frames.append(a_df)

    if not frames:
        return None, None, None

    combined = pd.concat(frames, ignore_index=True)

    garam_rows = []
    kistic_rows = []
    frozen_rows = []

    for _, row in combined.iterrows():
        p_name = str(row["상품명_원본"])
        opt_name = str(row["옵션_원본"])
        qty = int(row["상품수량"]) if pd.notnull(row["상품수량"]) else 1

        # 1. 부산어묵바 (가람식품) 판별
        if "어묵바" in p_name or "어묵바" in opt_name:
            # 옵션명 또는 상품명에서 어묵바 종류 추출
            target_name = "오리지날 부산어묵바"
            if "매콤달콤" in opt_name or "매콤달콤" in p_name:
                target_name = "매콤달콤 부산어묵바"
            elif "오징어야채" in opt_name or "오징어야채" in p_name:
                target_name = "오징어야채 부산어묵바"
            elif "체다치즈" in opt_name or "체다치즈" in p_name:
                target_name = "체다치즈 부산어묵바"

            # 합배송 불가: 수량만큼 행을 쪼개고 이름 뒤에 숫자 부여
            for i in range(qty):
                new_row = row.copy()
                new_row["수령자이름"] = (
                    f"{row['수령자이름']}{i+1}" if qty > 1 else row["수령자이름"]
                )
                new_row["상품명"] = target_name
                new_row[1] = 1  # 1개씩 개별 발주
                garam_rows.append(new_row)

        # 2. 키스틱 판별
        elif "키스틱" in p_name or "키스틱" in opt_name:
            is_40 = "40개" in p_name or "40개" in opt_name

            if is_40:
                if qty == 2:
                    # 40개 2개 -> 100개 1세트로 변환
                    new_row = row.copy()
                    new_row["상품명"] = "키스틱 15g x 100개"
                    new_row[1] = 1
                    kistic_rows.append(new_row)
                elif qty == 3:
                    # 홀수 분할: 40개 1세트 + 100개 1세트 (총 2행 생성)
                    row1 = row.copy()
                    row1["상품명"] = "키스틱 15g x 40개"
                    row1[1] = 1
                    kistic_rows.append(row1)

                    row2 = row.copy()
                    row2["수령자이름"] = f"{row['수령자이름']}2"
                    row2["상품명"] = "키스틱 15g x 100개"
                    row2[1] = 1
                    kistic_rows.append(row2)
                else:
                    # 일반 40개 처리
                    new_row = row.copy()
                    new_row["상품명"] = "키스틱 15g x 40개"
                    new_row[1] = qty
                    kistic_rows.append(new_row)
            else:
                # 100개 상품 그대로 반영
                new_row = row.copy()
                new_row["상품명"] = "키스틱 15g x 100개"
                new_row[1] = qty
                kistic_rows.append(new_row)

        # 3. 냉동식품 (고추잡채군만두, 김말이) 판별
        elif "만두" in p_name or "고추잡채" in p_name:
            new_row = row.copy()
            new_row["상품명"] = "더 바삭한 중화 고추잡채 군만두 1.2kg"
            new_row["상품수량"] = qty
            frozen_rows.append(new_row)

        elif "김말이" in p_name:
            new_row = row.copy()
            new_row["상품명"] = "김말이튀김400g"
            new_row["상품수량"] = qty * 3  # 기본 1세트당 3팩 곱하기
            frozen_rows.append(new_row)

    garam_df = pd.DataFrame(garam_rows) if garam_rows else None
    kistic_df = pd.DataFrame(kistic_rows) if kistic_rows else None
    frozen_df = pd.DataFrame(frozen_rows) if frozen_rows else None

    return garam_df, kistic_df, frozen_df
