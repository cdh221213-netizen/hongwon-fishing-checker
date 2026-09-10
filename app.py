from flask import Flask, jsonify
import requests
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


@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>홍원항 낚시 예약조회</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 60px auto;
                padding: 20px;
            }
            h1 {
                margin-bottom: 30px;
            }
            input, button {
                font-size: 18px;
                padding: 12px;
                margin: 5px 0;
            }
            button {
                cursor: pointer;
            }
            #result {
                margin-top: 30px;
                font-size: 20px;
                line-height: 1.8;
            }
        </style>
    </head>

    <body>

        <h1>🎣 홍원항 낚시 예약조회</h1>

        <input type="date" id="date">
        <button onclick="check()">조회하기</button>

        <div id="result"></div>

        <script>
            async function check() {
                const date = document.getElementById("date").value;

                if (!date) {
                    alert("날짜를 선택해주세요.");
                    return;
                }

                document.getElementById("result").innerHTML =
                    "조회 중...";

                const response =
                    await fetch("/newdaeho-date/" + date);

                const data = await response.json();

                if (!data.found) {
                    document.getElementById("result").innerHTML =
                        "조회 결과를 확인하지 못했습니다.";
                    return;
                }

                let statusText = data.status;

                if (data.status === "예약완료") {
                    statusText = "🔴 예약완료";
                } else if (data.status === "예약가능") {
                    statusText = "🟢 예약가능";
                }

                document.getElementById("result").innerHTML =
                    "<b>뉴대호</b><br>" +
                    data.date + "<br>" +
                    "<b>" + statusText + "</b>";
            }
        </script>

    </body>
    </html>
    """


@app.route("/newdaeho-date/<date_str>")
def newdaeho_date(date_str):
    try:
        selected_date = datetime.strptime(
            date_str,
            "%Y-%m-%d"
        )

        year = selected_date.year
        month = selected_date.month
        day = selected_date.day

        response = get_newdaeho_page(
            year,
            month,
            day
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        page_text = soup.get_text(
            " ",
            strip=True
        )

        date_text = (
            f"{year}년 {month:02d}월 {day:02d}일"
        )

        if date_text not in page_text:
            return jsonify({
                "ship": "뉴대호",
                "date": date_str,
                "found": False,
                "status": "확인불가"
            })

        status = "확인필요"

        rows = soup.find_all("tr")

        for row in rows:
            row_text = row.get_text(
                " ",
                strip=True
            )

            if "뉴대호피싱" in row_text:
                if "예약완료" in row_text:
                    status = "예약완료"
                elif (
                    "예약가능" in row_text
                    or "예약하기" in row_text
                ):
                    status = "예약가능"

                break

        return jsonify({
            "ship": "뉴대호",
            "date": date_str,
            "found": True,
            "status": status
        })

    except ValueError:
        return jsonify({
            "found": False,
            "message": "날짜 형식 오류"
        }), 400

    except Exception as e:
        return jsonify({
            "found": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=10000
    )
