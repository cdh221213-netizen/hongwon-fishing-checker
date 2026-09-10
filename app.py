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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
