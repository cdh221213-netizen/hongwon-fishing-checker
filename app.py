from flask import Flask, jsonify
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)

NEWDAEHO_BASE_URL = "http://www.newdaeho.com/index.php"


# =========================================================
# 뉴대호 페이지 가져오기
# =========================================================

def get_newdaeho_page(year, month, day):

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/152.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    }

    params = {
        "mid": "bk",
        "year": str(year),
        "month": f"{month:02d}",
        "day": f"{day:02d}",
        "mode": "list",
        "won": "1",
        "PA_N_UID": "0",
        "sel": "day#list"
    }

    response = requests.get(
        NEWDAEHO_BASE_URL,
        params=params,
        headers=headers,
        timeout=20,
        allow_redirects=True
    )

    response.raise_for_status()

    response.encoding = response.apparent_encoding

    return response


# =========================================================
# 숫자 추출
# =========================================================

def extract_remaining_number(text):

    patterns = [
        r"남은자리\s*[:：]?\s*(\d+)",
        r"잔여자리\s*[:：]?\s*(\d+)",
        r"잔여\s*[:：]?\s*(\d+)",
        r"남은\s*자리\s*[:：]?\s*(\d+)",
        r"(\d+)\s*석\s*남",
        r"(\d+)\s*자리\s*남"
    ]

    for pattern in patterns:

        match = re.search(pattern, text)

        if match:

            try:
                return int(match.group(1))

            except ValueError:
                pass

    clean = text.strip()

    if re.fullmatch(r"\d+", clean):

        try:
            return int(clean)

        except ValueError:
            return None

    return None


# =========================================================
# 뉴대호 예약현황 분석
# =========================================================

def check_newdaeho(date_str):

    selected = datetime.strptime(
        date_str,
        "%Y-%m-%d"
    )

    response = get_newdaeho_page(
        selected.year,
        selected.month,
        selected.day
    )

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    page_text = soup.get_text(
        " ",
        strip=True
    )

    # -----------------------------------------------------
    # 요청 날짜가 실제 페이지에 있는지 확인
    # -----------------------------------------------------

    date_patterns = [
        f"{selected.year}년 {selected.month:02d}월 {selected.day:02d}일",
        f"{selected.year}년 {selected.month}월 {selected.day}일",
        f"{selected.month:02d}월 {selected.day:02d}일",
        f"{selected.month}월 {selected.day}일"
    ]

    date_found = False

    for date_pattern in date_patterns:

        if date_pattern in page_text:
            date_found = True
            break

    if not date_found:

        return {
            "status": "unknown",
            "remaining": None,
            "message": "해당 날짜 예약정보 확인필요"
        }

    # -----------------------------------------------------
    # 예약표 찾기
    # -----------------------------------------------------

    reservation_table = None

    for table in soup.find_all("table"):

        table_text = table.get_text(
            " ",
            strip=True
        )

        if (
            "예약현황" in table_text
            and "남은자리" in table_text
        ):
            reservation_table = table
            break

    if reservation_table is None:

        return {
            "status": "unknown",
            "remaining": None,
            "message": "예약표 확인필요"
        }

    # -----------------------------------------------------
    # 뉴대호 행 찾기
    # -----------------------------------------------------

    ship_row = None

    possible_names = [
        "뉴대호피싱",
        "뉴대호"
    ]

    for tr in reservation_table.find_all("tr"):

        row_text = tr.get_text(
            " ",
            strip=True
        )

        for ship_name in possible_names:

            if ship_name in row_text:
                ship_row = tr
                break

        if ship_row is not None:
            break

    if ship_row is None:

        return {
            "status": "unknown",
            "remaining": None,
            "message": "뉴대호 예약행 확인필요"
        }

    # -----------------------------------------------------
    # 행 전체 정보 수집
    # -----------------------------------------------------

    row_text = ship_row.get_text(
        " ",
        strip=True
    )

    row_extra = []

    for img in ship_row.find_all("img"):

        alt = img.get("alt")
        title = img.get("title")
        src = img.get("src")

        if alt:
            row_extra.append(str(alt))

        if title:
            row_extra.append(str(title))

        if src:
            row_extra.append(str(src))

    for tag in ship_row.find_all(
        ["a", "button", "input"]
    ):

        text = tag.get_text(
            " ",
            strip=True
        )

        if text:
            row_extra.append(text)

        for attr in [
            "title",
            "value",
            "href"
        ]:

            value = tag.get(attr)

            if value:
                row_extra.append(str(value))

    combined_row = (
        row_text
        + " "
        + " ".join(row_extra)
    )

    # -----------------------------------------------------
    # 예약완료 판정
    # -----------------------------------------------------

    full_words = [
        "예약완료",
        "예약마감",
        "마감완료"
    ]

    for word in full_words:

        if word in combined_row:

            return {
                "status": "full",
                "remaining": 0,
                "message": "예약완료"
            }

    # -----------------------------------------------------
    # 남은자리 칸 찾기
    # -----------------------------------------------------

    cells = ship_row.find_all("td")

    remaining_candidates = []

    if cells:

        # 일반적으로 가장 오른쪽 칸이 남은자리
        last_cells = cells[-3:]

        for cell in last_cells:

            cell_parts = []

            cell_text = cell.get_text(
                " ",
                strip=True
            )

            if cell_text:
                cell_parts.append(cell_text)

            for img in cell.find_all("img"):

                alt = img.get("alt")
                title = img.get("title")
                src = img.get("src")

                if alt:
                    cell_parts.append(str(alt))

                if title:
                    cell_parts.append(str(title))

                if src:
                    cell_parts.append(str(src))

            for tag in cell.find_all(
                ["a", "button", "input"]
            ):

                tag_text = tag.get_text(
                    " ",
                    strip=True
                )

                if tag_text:
                    cell_parts.append(tag_text)

                value = tag.get("value")

                if value:
                    cell_parts.append(str(value))

            remaining_candidates.append(
                " ".join(cell_parts)
            )

    # -----------------------------------------------------
    # 각 후보에서 남은자리 숫자 추출
    # -----------------------------------------------------

    remaining = None

    for candidate in reversed(
        remaining_candidates
    ):

        number = extract_remaining_number(
            candidate
        )

        if number is not None:

            remaining = number
            break

    # -----------------------------------------------------
    # 행 전체에서도 남은자리 표현 확인
    # -----------------------------------------------------

    if remaining is None:

        remaining = extract_remaining_number(
            combined_row
        )

    # -----------------------------------------------------
    # 숫자를 실제로 찾았을 때만 예약가능 판정
    # -----------------------------------------------------

    if remaining is not None:

        if remaining <= 0:

            return {
                "status": "full",
                "remaining": 0,
                "message": "예약완료"
            }

        return {
            "status": "available",
            "remaining": remaining,
            "message": f"예약가능 · 남은자리 {remaining}석"
        }

    # -----------------------------------------------------
    # 아무것도 확실히 확인하지 못한 경우
    # 절대 예약가능으로 판정하지 않는다.
    # -----------------------------------------------------

    return {
        "status": "unknown",
        "remaining": None,
        "message": "남은자리 확인필요"
    }


# =========================================================
# 메인 홈페이지
# =========================================================

@app.route("/")
def home():

    return """
<!DOCTYPE html>

<html lang="ko">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>
홍원항 낚시 빈자리 조회
</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #f4f6f8;
    color: #111;
}

.container {
    width: 90%;
    max-width: 650px;
    margin: 60px auto;
    padding: 35px;
    background: white;
    border-radius: 18px;
    box-shadow: 0 5px 20px rgba(0,0,0,0.08);
}

h1 {
    margin-top: 0;
    font-size: 30px;
}

.description {
    margin-top: 15px;
    color: #555;
}

.search {
    display: flex;
    gap: 10px;
    margin-top: 28px;
}

input {
    flex: 1;
    padding: 14px;
    font-size: 17px;
    border: 1px solid #aaa;
    border-radius: 5px;
}

button {
    padding: 14px 22px;
    font-size: 17px;
    cursor: pointer;
    border: 1px solid #999;
    border-radius: 5px;
    background: #f5f5f5;
}

button:hover {
    background: #e8e8e8;
}

.card {
    display: none;
    margin-top: 28px;
    padding: 22px;
    background: #f7f7f7;
    border-radius: 12px;
}

.ship {
    font-size: 23px;
    font-weight: bold;
}

.date {
    margin-top: 8px;
    color: #555;
}

.status {
    margin-top: 16px;
    font-size: 21px;
    font-weight: bold;
}

.note {
    margin-top: 25px;
    padding-top: 18px;
    border-top: 1px solid #ddd;
    color: #777;
    font-size: 14px;
    line-height: 1.6;
}

@media (max-width: 600px) {

    .container {
        margin: 20px auto;
        padding: 22px;
    }

    h1 {
        font-size: 25px;
    }

    .search {
        flex-direction: column;
    }

    button {
        width: 100%;
    }
}

</style>

</head>


<body>

<div class="container">

    <h1>
        🎣 홍원항 낚시 빈자리 조회
    </h1>

    <div class="description">
        날짜를 선택하면 선박별 예약현황과
        남은자리를 확인합니다.
    </div>

    <div class="search">

        <input
            type="date"
            id="date"
            value="2026-09-21"
        >

        <button onclick="checkReservation()">
            조회하기
        </button>

    </div>

    <div
        id="card"
        class="card"
    >

        <div class="ship">
            뉴대호
        </div>

        <div
            id="resultDate"
            class="date"
        >
        </div>

        <div
            id="status"
            class="status"
        >
        </div>

    </div>

    <div class="note">
        현재 뉴대호 예약정보 추출 기능을 검증 중입니다.
        정확한 판정이 완료되면 다른 홍원항 선박도
        한 번에 조회하도록 추가합니다.
    </div>

</div>


<script>

async function checkReservation() {

    const dateInput =
        document.getElementById("date");

    const date =
        dateInput.value;

    if (!date) {

        alert(
            "날짜를 선택해주세요."
        );

        return;
    }

    const card =
        document.getElementById("card");

    const status =
        document.getElementById("status");

    const resultDate =
        document.getElementById(
            "resultDate"
        );

    card.style.display =
        "block";

    resultDate.textContent =
        date;

    status.textContent =
        "⏳ 조회 중...";

    try {

        const response =
            await fetch(
                "/api/newdaeho/" + date
            );

        const data =
            await response.json();

        if (
            data.status === "full"
        ) {

            status.textContent =
                "🔴 예약완료 · 남은자리 0석";

        }

        else if (
            data.status === "available"
        ) {

            status.textContent =
                "🟢 예약가능 · 남은자리 "
                + data.remaining
                + "석";

        }

        else if (
            data.status === "error"
        ) {

            status.textContent =
                "⚠️ 조회 오류";

        }

        else {

            status.textContent =
                "🟡 남은자리 확인필요";

        }

    }

    catch (error) {

        status.textContent =
            "⚠️ 조회 오류";

    }
}

</script>

</body>

</html>
"""


# =========================================================
# API
# =========================================================

@app.route("/api/newdaeho/<date_str>")
def api_newdaeho(date_str):

    try:

        result = check_newdaeho(date_str)

        result["ship"] = "뉴대호"
        result["date"] = date_str

        return jsonify(result)

    except ValueError:

        return jsonify({
            "status": "error",
            "ship": "뉴대호",
            "date": date_str,
            "message": "날짜 형식 오류"
        }), 400

    except Exception as e:

        return jsonify({
            "status": "error",
            "ship": "뉴대호",
            "date": date_str,
            "message": str(e)
        }), 500


# =========================================================
# 서버 실행
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=10000
    )
