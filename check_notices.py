"""
서강대학교 공지사항 모니터링 -> 디스코드 알림
매일 GitHub Actions로 실행됨
"""
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import feedparser

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
SEEN_FILE = Path(__file__).parent / "seen_posts.json"

# 모니터링할 게시판 목록
# type "cms": 레거시 cmsboardlist.do 패턴 (단순 HTML 스크래핑)
# type "rss": 워드프레스 등 RSS 피드 제공 사이트
BOARDS = [
    {"type": "cms", "name": "사학과 공지", "url": "https://history.sogang.ac.kr/front/cmsboardlist.do?siteId=history&bbsConfigFK=626"},
    {"type": "cms", "name": "인문대학 공지", "url": "https://liberalarts.sogang.ac.kr/front/cmsboardlist.do?siteId=liberalarts&bbsConfigFK=4066"},
    {"type": "cms", "name": "글쓰기센터 공지", "url": "https://writing.sogang.ac.kr/front/cmsboardlist.do?siteId=writing&bbsConfigFK=1"},
    {"type": "cms", "name": "HUSS 포용사회사업단", "url": "https://scc.sogang.ac.kr/front/cmsboardlist.do?siteId=sogangiis&bbsConfigFK=7972"},
    {"type": "rss", "name": "아트&테크놀로지학과 뉴스", "url": "https://creative.sogang.ac.kr/feed/"},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SogangNoticeBot/1.0; personal use)"
}


def load_seen():
    if SEEN_FILE.exists():
        return json.loads(SEEN_FILE.read_text(encoding="utf-8"))
    return {}


def save_seen(seen):
    SEEN_FILE.write_text(json.dumps(seen, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_cms_board(board):
    """게시판 목록 페이지에서 글 목록을 추출.
    cmsboardview.do 링크를 가진 <a> 태그를 모두 찾아서 (pkid, 제목, url) 추출.
    """
    resp = requests.get(board["url"], headers=HEADERS, timeout=15)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    posts = []
    seen_pkids_on_page = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "cmsboardview.do" not in href:
            continue
        m = re.search(r"pkid=(\d+)", href)
        if not m:
            continue
        pkid = m.group(1)
        if pkid in seen_pkids_on_page:
            continue
        seen_pkids_on_page.add(pkid)
        title = a.get_text(strip=True)
        if not title:
            continue
        full_url = urljoin(board["url"], href)
        posts.append({"pkid": pkid, "title": title, "url": full_url})
    return posts


def fetch_rss_board(board):
    """RSS 피드에서 글 목록 추출. pkid 대신 글 링크(guid/link)를 고유 ID로 사용."""
    feed = feedparser.parse(board["url"])
    posts = []
    for entry in feed.entries:
        uid = getattr(entry, "id", None) or entry.link
        posts.append({"pkid": uid, "title": entry.title, "url": entry.link})
    return posts


def fetch_board(board):
    if board["type"] == "rss":
        return fetch_rss_board(board)
    return fetch_cms_board(board)


def send_discord(board_name, new_posts):
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_URL이 설정 안 됨, 알림 스킵")
        return
    lines = [f"**[{board_name}]** 새 글 {len(new_posts)}건"]
    for p in new_posts:
        lines.append(f"- [{p['title']}]({p['url']})")
    content = "\n".join(lines)
    # 디스코드 메시지 길이 제한(2000자) 대응
    if len(content) > 1900:
        content = content[:1900] + "\n...(생략)"
    resp = requests.post(DISCORD_WEBHOOK_URL, json={"content": content}, timeout=15)
    resp.raise_for_status()


def main():
    seen = load_seen()
    any_new = False

    for board in BOARDS:
        board_key = board["url"]
        seen_ids = set(seen.get(board_key, []))
        try:
            posts = fetch_board(board)
        except Exception as e:
            print(f"[에러] {board['name']} 가져오기 실패: {e}", file=sys.stderr)
            continue

        new_posts = [p for p in posts if p["pkid"] not in seen_ids]

        # 첫 실행(seen 기록이 전혀 없는 게시판)은 전체를 새 글로 보내지 않고
        # 그냥 현재 목록을 기준점으로만 저장 (스팸 방지)
        if board_key not in seen:
            print(f"[{board['name']}] 첫 실행, 기준점만 저장 ({len(posts)}건)")
        elif new_posts:
            print(f"[{board['name']}] 새 글 {len(new_posts)}건 발견")
            send_discord(board["name"], new_posts)
            any_new = True
        else:
            print(f"[{board['name']}] 새 글 없음")

        seen[board_key] = [p["pkid"] for p in posts]

    save_seen(seen)
    if not any_new:
        print("오늘은 새로 올라온 공지 없음")


if __name__ == "__main__":
    main()
