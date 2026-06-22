# 서강대 공지 디스코드 알림 봇

매일 자동으로 사강 게시판들을 확인하고 새 글이 올라오면 디스코드로 알려줌.
스크립트 2개로 나뉨:
- `check_notices.py` — 사학과/인문대학/글쓰기센터/HUSS/아트테크놀로지(레거시 CMS + RSS)
- `check_notices_main_site.py` — 일반공지/학사공지/장학공지/학생일반공지/행사특강 (메인 사이트, JS 렌더링이라 Playwright 사용)

## 셋업 방법 (한 번만 하면 됨)

### 1. 디스코드 웹훅 만들기
1. 알림 받고 싶은 디스코드 채널의 설정 들어가기
2. "연동" → "웹후크" → "새 웹후크 만들기"
3. 이름 정하고 "웹후크 URL 복사" (이 URL은 비밀번호처럼 다뤄야 함, 아무 데나 올리지 말 것)

### 2. GitHub 저장소 만들고 파일 올리기
1. github.com 가입/로그인 → 우측 상단 "+" → "New repository"
2. 이름 정하고(예: `sogang-notifier`) Private로 설정 → Create
3. 이 zip 안의 파일들을 그 저장소에 그대로 업로드 (폴더 구조 그대로: `.github/workflows/` 포함)
   - 깃허브 웹사이트에서 "Add file" → "Upload files"로 드래그해서 올리면 됨

### 3. 디스코드 웹훅 URL을 깃허브 시크릿에 등록
1. 저장소 페이지 → Settings → Secrets and variables → Actions
2. "New repository secret" 클릭
3. Name: `DISCORD_WEBHOOK_URL`
4. Value: 1번에서 복사한 웹훅 URL 붙여넣기 → Add secret

### 4. 끝, 자동 실행 확인
- 매일 한국시간 오전 8시(+10분)에 두 스크립트 다 자동 실행됨
- 저장소 페이지 → Actions 탭에서 "Run workflow" 누르면 지금 바로 수동 실행도 가능
- 처음 실행할 때는 "기준점"만 저장하고 알림은 안 보냄 (그 이후에 올라오는 새 글부터 알림 옴)
- 에러 나면 Actions 탭에서 빨간 X 표시된 실행 기록 클릭하면 에러 로그 볼 수 있음, 그거 캡처해서 보여주면 같이 고칠 수 있음

## 처리 못 한 부분
- **job.sogang.ac.kr (취업지원팀)**: robots.txt가 자동 수집을 명시적으로 막아놔서 스크립트 대상에서 제외함. 직접 가끔 확인 필요.
- **국제처 교환학생 관련 페이지**: 정확히 어느 페이지가 아웃바운드 교환학생 공지인지 추가 확인 필요(outbound.sogang.ac.kr 등), 확인되면 추가 가능.

## 게시판 추가하고 싶을 때
- `check_notices.py`의 `BOARDS` 리스트에 `{"type": "cms"|"rss", "name": "이름", "url": "..."}` 추가
- 워드프레스 사이트는 보통 `사이트주소/feed/`가 RSS 피드 URL임

## 로그인이 필요한 게시판은?
스크립트에 직접 비밀번호를 적지 말 것. 깃허브 시크릿에 별도 등록(예: `SOGANG_ID`, `SOGANG_PW`)하고,
스크립트에서 `os.environ.get("SOGANG_ID")`처럼 불러와서 쓰면 됨.
