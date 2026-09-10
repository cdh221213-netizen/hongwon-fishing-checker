from flask import Flask, jsonify
import requests
import re
from bs4 import BeautifulSoup

app = Flask(__name__)

NEWDAEHO_URL = "http://www.newdaeho.com/index.php?mid=bk"


def get_newdaeho_text():
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

    return response, text


@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "service": "Hongwon Fishing Checker",
        "message": "서버가 정상적으로 실행 중입니다."
    })


@app.route("/newdaeho")
def check_newdaeho():
    try:
        response, text = get_newdaeho_text()

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
    try:
        response, text = get_newdaeho_text()
        return text

    except Exception as e:
        return str(e), 500


@app.route("/newdaeho-date/<date_str>")
def newdaeho_date(date_str):
    try:
        year, month, day = map(int, date_str.split("-"))

        response, text = get_newdaeho_text()

        pattern = re.compile(
            rf"{year}년\s*0?{month}월\s*0?{day}일"
        )

        match = pattern.search(text)

        if not match:
            return jsonify({
                "ship": "뉴대호",
                "date": date_str,
                "found": False,
                "message": "해당 날짜를 찾지 못했습니다."
            })

        start = match.start()

        next_date_pattern = re.compile(
            r"\d{4}년\s*\d{1,2}월\s*\d{1,2}일"
        )

        next_match = next_date_pattern.search(text, match.end())

        if next_match:
            section = text[start:next_match.start()]
        else:
            section = text[start:start + 3000]

        return jsonify({
            "ship": "뉴대호",
            "date": date_str,
            "found": True,
            "result": section
        })

    except ValueError:
        return jsonify({
            "ship": "뉴대호",
            "date": date_str,
            "found": False,
            "message": "날짜 형식은 YYYY-MM-DD로 입력해주세요."
        }), 400

    except Exception as e:
        return jsonify({
            "ship": "뉴대호",
            "date": date_str,
            "found": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
