"""
서강대 메인 사이트(sogang.ac.kr)의 자바스크립트 렌더링 게시판용 스크래퍼.
일반 requests로는 빈 화면만 나와서 Playwright(헤드리스 브라우저)로 렌더링 후 추출.
"""
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
SEEN_FILE = Path(__file__).parent / "seen_posts_main.json"

BOARDS = [
    {"name": "일반공지", "url": "https://www.sogang.ac.kr/ko/story/notification-general"},
    {"name": "학부 학사공지", "url": "https://www.sogang.ac.kr/ko/academic-support/notices"},
    {"name": "장학공지", "url": "https://www.sogang.ac.kr/ko/scholarship-notice"},
    {"name": "학생 일반공지", "url": "https://www.sogang.ac.kr/ko/campus/student-support/notice"},
    {"name": "행사특강", "url": "https://www.sogang.ac.kr/ko/story/notification-event"},
]

DETAIL_PATTERN = re.compile(r"/ko/detail/(\d+)")


def load_seen():
    if SEEN_FILE.exists():
        return json.loads(SEEN_FILE.read_text(encoding="utf-8"))
    return {}


def save_seen(seen):
    SEEN_FILE.write_text(json.dumps(seen, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_board(page, board):
    page.goto(board["url"], wait_until="networkidle", timeout=30000)
    # 목록이 비동기로 더 늦게 뜨는 경우 대비해 약간 더 대기
    page.wait_for_timeout(2000)

    anchors = page.eval_on_selector_all(
        "a[href*='/ko/detail/']",
        "els => els.map(e => ({href: e.getAttribute('href'), text: e.textContent}))",
    )

    posts = []
    seen_ids = set()
    for a in anchors:
        href = a.get("href") or ""
        m = DETAIL_PATTERN.search(href)
        if not m:
            continue
        pkid = m.group(1)
        if pkid in seen_ids:
            continue
        seen_ids.add(pkid)
        title = (a.get("text") or "").strip()
        if not title:
            continue
        posts.append({
            "pkid": pkid,
            "title": title,
            "url": urljoin(board["url"], href),
        })
    return posts


def send_discord(board_name, new_posts):
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URL이 설정 안 됨, 알림 스킵")
        return
    import requests
    lines = [f"**[{board_name}]** 새 글 {len(new_posts)}건"]
    for p in new_posts:
        lines.append(f"- [{p['title']}]({p['url']})")
    content = "\n".join(lines)
    if len(content) > 1900:
        content = content[:1900] + "\n...(생략)"
    resp = requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=15)
    resp.raise_for_status()


def main():
    seen = load_seen()
    any_new = False

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        for board in BOARDS:
            board_key = board["url"]
            seen_ids = set(seen.get(board_key, []))
            try:
                posts = fetch_board(page, board)
            except Exception as e:
                print(f"[에러] {board['name']} 가져오기 실패: {e}", file=sys.stderr)
                continue

            new_posts = [post for post in posts if post["pkid"] not in seen_ids]

            if board_key not in seen:
                print(f"[{board['name']}] 첫 실행, 기준점만 저장 ({len(posts)}건)")
            elif new_posts:
                print(f"[{board['name']}] 새 글 {len(new_posts)}건 발견")
                send_discord(board["name"], new_posts)
                any_new = True
            else:
                print(f"[{board['name']}] 새 글 없음")

            seen[board_key] = [post["pkid"] for post in posts]

        browser.close()

    save_seen(seen)
    if not any_new:
        print("오늘은 새로 올라온 공지 없음 (메인 사이트)")


if __name__ == "__main__":
    main()
