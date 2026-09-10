from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)

NEWDAEHO_BASE_URL = "http://www.newdaeho.com/index.php"


def get_page(year, month, day):
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


def check_reservation(date_str):
    selected = datetime.strptime(date_str, "%Y-%m-%d")

    response = get_page(
        selected.year,
        selected.month,
        selected.day
    )

    soup = BeautifulSoup(response.text, "html.parser")

    # 뉴대호피싱이 들어있는 행을 찾는다.
    target_row = None

    for tr in soup.find_all("tr"):
        text = tr.get_text(" ", strip=True)

        if "뉴대호피싱" in text:
            target_row = tr
            break

    # 사이트 구조에 따라 td 내부에 있을 수도 있으므로 한 번 더 검색
    if target_row is None:
        target_text = soup.find(
            string=lambda x: x and "뉴대호피싱" in x
        )

        if target_text:
            target_row = target_text.find_parent("tr")

    if target_row is None:
        return {
            "status": "unknown",
            "message": "뉴대호피싱 예약정보를 찾지 못했습니다."
        }

    # 해당 행의 모든 이미지 alt 확인
    image_alts = []

    for img in target_row.find_all("img"):
        alt = img.get("alt")

        if alt:
            image_alts.append(alt.strip())

    # 예약완료 이미지 확인
    if "예약완료" in image_alts:
        return {
            "status": "full",
            "message": "예약완료"
        }

    # 행 전체 텍스트
    row_text = target_row.get_text(
        " ",
        strip=True
    )

    # 남은자리 숫자가 직접 텍스트로 표시되는 경우
    import re

    patterns = [
        r"남은자리\s*(\d+)",
        r"남은자리\s*[:：]?\s*(\d+)",
        r"잔여\s*(\d+)",
        r"(\d+)\s*자리"
    ]

    for pattern in patterns:
        match = re.search(pattern, row_text)

        if match:
            seats = int(match.group(1))

            return {
                "status": "available",
                "remaining": seats,
                "message": f"예약가능 · 남은자리 {seats}석"
            }

    # 예약완료 이미지가 없으면 일단 예약 가능 상태로 판정하되
    # 좌석 숫자를 확인하지 못한 경우
    return {
        "status": "available",
        "remaining": None,
        "message": "예약가능"
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

<title>홍원항 낚시 예약조회</title>

<style>

body {
    font-family: Arial, sans-serif;
    background:#f5f7fa;
    margin:0;
}

.container {
    max-width:600px;
    margin:70px auto;
    background:white;
    padding:35px;
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
    font-size:17px;
    padding:12px;
    flex:1;
}

button {
    font-size:17px;
    padding:12px 20px;
    cursor:pointer;
}

.result {
    margin-top:30px;
    padding:22px;
    background:#f7f7f7;
    border-radius:12px;
    display:none;
}

.ship {
    font-size:22px;
    font-weight:bold;
    margin-bottom:10px;
}

.status {
    font-size:20px;
    font-weight:bold;
}

.date {
    margin-bottom:15px;
    color:#555;
}

</style>

</head>

<body>

<div class="container">

<h1>🎣 홍원항 낚시 예약조회</h1>

<p>날짜를 선택하면 뉴대호 예약현황을 확인합니다.</p>

<div class="search">

<input
type="date"
id="date"
value="2026-09-21">

<button onclick="check()">
조회하기
</button>

</div>

<div id="result" class="result">

<div class="ship">
뉴대호
</div>

<div id="resultDate" class="date"></div>

<div id="status" class="status">
조회 중...
</div>

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

    const box =
        document.getElementById("result");

    const status =
        document.getElementById("status");

    const resultDate =
        document.getElementById("resultDate");

    box.style.display = "block";

    resultDate.textContent = date;

    status.textContent = "⏳ 조회 중...";

    try {

        const response =
            await fetch("/api/check/" + date);

        const data =
            await response.json();

        if (data.status === "full") {

            status.textContent =
                "🔴 예약완료";

        }

        else if (data.status === "available") {

            if (data.remaining !== null &&
                data.remaining !== undefined) {

                status.textContent =
                    "🟢 예약가능 · 남은자리 "
                    + data.remaining
                    + "석";

            }

            else {

                status.textContent =
                    "🟢 예약가능";

            }

        }

        else {

            status.textContent =
                "🟡 확인필요";

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


@app.route("/api/check/<date_str>")
def api_check(date_str):

    try:

        result = check_reservation(date_str)

        result["ship"] = "뉴대호"
        result["date"] = date_str

        return jsonify(result)

    except Exception as e:

        return jsonify({
            "ship": "뉴대호",
            "date": date_str,
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=10000
    )
