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
        <title>뉴대호 구조 확인</title>
    </head>

    <body style="font-family:Arial; max-width:900px; margin:40px auto;">

        <h1>뉴대호 HTML 구조 확인</h1>

        <input type="date" id="date" value="2026-09-21">
        <button onclick="check()">확인하기</button>

        <pre id="result"
             style="
             white-space:pre-wrap;
             word-break:break-all;
             background:#f5f5f5;
             padding:20px;
             margin-top:20px;
             "></pre>

        <script>
            async function check() {
                const date =
                    document.getElementById("date").value;

                const result =
                    document.getElementById("result");

                result.textContent = "조회 중...";

                const response =
                    await fetch("/debug/" + date);

                const data =
                    await response.json();

                result.textContent =
                    data.debug_html || JSON.stringify(data, null, 2);
            }
        </script>

    </body>
    </html>
    """


@app.route("/debug/<date_str>")
def debug_page(date_str):

    try:
        selected_date = datetime.strptime(
            date_str,
            "%Y-%m-%d"
        )

        response = get_newdaeho_page(
            selected_date.year,
            selected_date.month,
            selected_date.day
        )

        html = response.text

        position = html.find("뉴대호피싱")

        if position == -1:
            return jsonify({
                "found": False,
                "message": "뉴대호피싱 문자열을 HTML에서 찾지 못했습니다."
            })

        start = max(0, position - 3000)
        end = min(len(html), position + 5000)

        debug_html = html[start:end]

        return jsonify({
            "found": True,
            "date": date_str,
            "debug_html": debug_html
        })

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
