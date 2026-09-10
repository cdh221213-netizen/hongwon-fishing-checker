from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup

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
        timeout=20,
        allow_redirects=True
    )

    response.raise_for_status()
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


@app.route("/newdaeho-date/<date_str>")
def newdaeho_date(date_str):
    try:
        parts = date_str.split("-")

        if len(parts) != 3:
            raise ValueError

        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])

        response, text = get_newdaeho_page(
            year,
            month,
            day
        )

        target1 = f"{year}년 {month:02d}월 {day:02d}일"
        target2 = f"{year}년 {month}월 {day}일"

        if target1 not in text and target2 not in text:
            return jsonify({
                "ship": "뉴대호",
                "date": date_str,
                "found": False,
                "message": "해당 날짜의 예약 페이지를 찾지 못했습니다.",
                "source_url": response.url
            })

        if "예약완료" in text:
            status = "예약완료"
        elif "예약가능" in text:
            status = "예약가능"
        else:
            status = "확인필요"

        return jsonify({
            "ship": "뉴대호",
            "date": date_str,
            "found": True,
            "status": status,
            "source_url": response.url,
            "result": text[:5000]
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
