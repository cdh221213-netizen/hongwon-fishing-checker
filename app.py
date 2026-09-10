from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

NEWDAEHO_URL = "http://www.newdaeho.com/index.php?mid=bk"


@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "service": "Hongwon Fishing Checker",
        "message": "서버가 정상적으로 실행 중입니다."
    })


@app.route("/newdaeho")
def check_newdaeho():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/152.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    }

    try:
        response = requests.get(
            NEWDAEHO_URL,
            headers=headers,
            timeout=20,
            allow_redirects=True
        )

        response.encoding = response.apparent_encoding

        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.title.get_text(strip=True) if soup.title else None

        return jsonify({
            "ship": "뉴대호",
            "url": NEWDAEHO_URL,
            "status_code": response.status_code,
            "final_url": response.url,
            "page_title": title,
            "content_length": len(response.text),
            "success": response.ok
        })

    except Exception as e:
        return jsonify({
            "ship": "뉴대호",
            "success": False,
            "error": str(e)
        }), 500

   


@app.route("/newdaeho-text")
def newdaeho_text():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/152.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    }

    try:
        response = requests.get(
            NEWDAEHO_URL,
            headers=headers,
            timeout=20,
            allow_redirects=True
        )

        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text("\n", strip=True)

        return text

    except Exception as e:
        return str(e), 500
@app.route("/newdaeho-date/<date_str>")
def newdaeho_date(date_str):
    import re

    try:
        parts = date_str.split("-")
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])

        target = f"{year}년 {month:02d}월 {day:02d}일"

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/152.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        }

        response = requests.get(
            NEWDAEHO_URL,
            headers=headers,
            timeout=20,
            allow_redirects=True
        )

        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(" ", strip=True)

        start = text.find(target)

        if start == -1:
            return jsonify({
                "ship": "뉴대호",
                "date": date_str,
                "found": False,
                "message": "해당 날짜를 찾지 못했습니다."
            })

        after = text[start + len(target):]

        next_date = re.search(
            r"2026년 \d{2}월 \d{2}일",
            after
        )

        if next_date:
            section = text[start:start + len(target) + next_date.start()]
        else:
            section = text[start:start + 3000]

        return jsonify({
            "ship": "뉴대호",
            "date": date_str,
            "found": True,
            "result": section
        })

    except Exception as e:
        return jsonify({
            "ship": "뉴대호",
            "date": date_str,
            "found": False,
            "error": str(e)
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
