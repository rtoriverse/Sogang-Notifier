"""
매일 한국시간 오전 6시에 그날 시간표를 디스코드로 보내는 스크립트.
schedule_data.json에서 오늘 날짜(KST 기준)에 해당하는 일정을 찾아서 전송.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
DATA_FILE = Path(__file__).parent / "schedule_data.json"

KST = ZoneInfo("Asia/Seoul")


def load_data():
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def today_kst_str():
    return datetime.now(KST).strftime("%Y-%m-%d")


def format_message(date_str, day):
    md = datetime.strptime(date_str, "%Y-%m-%d")
    lines = [f"**📅 {md.month}월 {md.day}일 · {day['label']}**"]
    for time_label, text in day["items"]:
        lines.append(f"`{time_label}` {text}")
    return "\n".join(lines)


def send_discord(content):
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URL이 설정 안 됨")
        return
    resp = requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=15)
    resp.raise_for_status()


def main():
    data = load_data()
    today = today_kst_str()
    day = data.get(today)

    if day is None:
        send_discord(f"오늘({today})은 아직 시간표에 등록된 일정이 없어. 추가해줘!")
        print(f"{today}: 등록된 일정 없음")
        return

    message = format_message(today, day)
    send_discord(message)
    print(f"{today}: 일정 전송 완료")


if __name__ == "__main__":
    main()
