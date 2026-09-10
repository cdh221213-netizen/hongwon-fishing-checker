from flask import Flask, jsonify
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)

NEWDAEHO_BASE_URL = "http://www.newdaeho.com/index.php"


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
        timeout=20
    )

    response.raise_for_status()
    response.encoding = response.apparent_encoding

    return response


def extract_remaining_number(text):
    patterns = [
        r"남은자리\s*[:：]?\s*(\d+)",
        r"잔여\s*[:：]?\s*(\d+)",
        r"(\d+)\s*석",
        r"(\d+)\s*자리",
        r"(\d+)\s*명"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return int(match.group(1))

    # 남은자리 칸에 숫자 하나만 있는 경우
    clean = text.strip()

    if re.fullmatch(r"\d+", clean):
        return int(clean)

    return None


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

    # 선박명 / 예약현황 / 남은자리 헤더가 있는 예약표 찾기
    reservation_table = None

    for table in soup.find_all("table"):

        table_text = table.get_text(
            " ",
            strip=True
        )

        if (
            "선박명" in table_text
            and "예약현황" in table_text
            and "남은자리" in table_text
        ):
            reservation_table = table
            break

    if reservation_table is None:
        return {
            "status": "unknown",
            "remaining": None,
            "message": "예약표를 찾지 못했습니다."
        }

    # 뉴대호피싱 행 찾기
    ship_row = None

    for tr in reservation_table.find_all("tr"):

        row_text = tr.get_text(
            " ",
            strip=True
        )

        if "뉴대호피싱" in row_text:
            ship_row = tr
            break

    if ship_row is None:
        return {
            "status": "unknown",
            "remaining": None,
            "message": "뉴대호피싱 예약행을 찾지 못했습니다."
        }

    # 행 안의 칸(td) 확인
    cells = ship_row.find_all(
        "td",
        recursive=False
    )

    # 중첩 테이블 때문에 직접 td가 안 잡히는 경우
    if len(cells) < 2:
        cells = ship_row.find_all("td")

    if not cells:
        return {
            "status": "unknown",
            "remaining": None,
            "message": "남은자리 칸을 찾지 못했습니다."
        }

    # 화면상 오른쪽 마지막 칸이 '남은자리'
    remaining_cell = cells[-1]

    remaining_text = remaining_cell.get_text(
        " ",
        strip=True
    )

    # 이미지 alt/title 등도 함께 검사
    extra_text = []

    for img in remaining_cell.find_all("img"):

        for attr in ["alt", "title", "src"]:

            value = img.get(attr)

            if value:
                extra_text.append(str(value))

    for tag in remaining_cell.find_all(
        ["a", "button", "input"]
    ):

        for attr in [
            "title",
            "value",
            "class",
            "href"
        ]:

            value = tag.get(attr)

            if value:

                if isinstance(value, list):
                    value = " ".join(value)

                extra_text.append(str(value))

        tag_text = tag.get_text(
            " ",
            strip=True
        )

        if tag_text:
            extra_text.append(tag_text)

    combined = (
        remaining_text
        + " "
        + " ".join(extra_text)
    )

    # 1. 예약완료/마감
    if (
        "예약완료" in combined
        or "예약마감" in combined
        or "마감" in remaining_text
    ):
        return {
            "status": "full",
            "remaining": 0,
            "message": "예약완료"
        }

    # 2. 실제 남은자리 숫자 확인
    remaining = extract_remaining_number(
        combined
    )

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

    # 3. 숫자를 못 찾았으면 절대 예약가능으로 단정하지 않음
    return {
        "status": "unknown",
        "remaining": None,
        "message": "남은자리 확인필요",
        "debug_remaining_text": combined[:500]
    }


@app.route("/")
def home():

    return """
<!DOCTYPE html>
<html lang="ko">

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1.0">

<title>홍원항 낚시 빈자리 조회</title>

<style>

body {
    font-family: Arial, sans-serif;
    background:#f4f6f8;
    margin:0;
}

.container {
    max-width:650px;
    margin:60px auto;
    padding:35px;
    background:white;
    border-radius:18px;
    box-shadow:0 5px 20px rgba(0,0,0,0.08);
}

h1 {
    margin-top:0;
}

.search {
    display:flex;
    gap:10px;
    margin-top:25px;
}

input {
    flex:1;
    padding:14px;
    font-size:18px;
}

button {
    padding:14px 22px;
    font-size:18px;
    cursor:pointer;
}

.card {
    display:none;
    margin-top:30px;
    padding:22px;
    background:#f7f7f7;
    border-radius:12px;
}

.ship {
    font-size:23px;
    font-weight:bold;
}

.date {
    margin-top:6px;
    color:#666;
}

.status {
    margin-top:15px;
    font-size:21px;
    font-weight:bold;
}

.note {
    margin-top:25px;
    color:#777;
    font-size:14px;
}

</style>

</head>

<body>

<div class="container">

<h1>🎣 홍원항 낚시 빈자리 조회</h1>

<p>
날짜를 선택하면 선박별 예약현황과 남은자리를 확인합니다.
</p>

<div class="search">

<input
    type="date"
    id="date"
    value="2026-09-21"
>

<button onclick="check()">
조회하기
</button>

</div>

<div id="card" class="card">

<div class="ship">
뉴대호
</div>

<div
    id="resultDate"
    class="date">
</div>

<div
    id="status"
    class="status">
</div>

</div>

<div class="note">
현재 뉴대호 예약정보 추출 규칙을 검증 중이며,
이후 다른 홍원항 선박도 같은 화면에 추가할 예정입니다.
</div>

</div>


<script>

async function check() {

    const date =
        document.getElementById("date").value;

    if (!date) {
        alert("날짜를 선택해주세요.");
        return;
    }

    const card =
        document.getElementById("card");

    const status =
        document.getElementById("status");

    document.getElementById(
        "resultDate"
    ).textContent = date;

    card.style.display = "block";

    status.textContent =
        "⏳ 조회 중...";

    try {

        const response =
            await fetch(
                "/api/newdaeho/" + date
            );

        const data =
            await response.json();

        if (data.status === "full") {

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

        else {

            status.textContent =
                "🟡 남은자리 확인필요";

        }

    }

    catch(error) {

        status.textContent =
            "⚠️ 조회 오류";

    }

}

</script>

</body>
</html>
"""


@app.route("/api/newdaeho/<date_str>")
def api_newdaeho(date_str):

    try:

        result =
            check_newdaeho(date_str)

        result["ship"] = "뉴대호"
        result["date"] = date_str

        return jsonify(result)

    except ValueError:

        return jsonify({
            "status": "error",
            "message": "날짜 형식 오류"
        }), 400

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=10000
    )
