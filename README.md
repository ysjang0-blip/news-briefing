# 아침 뉴스 브리핑

매일 아침 7시(한국시간), 관심 키워드의 뉴스를 모아 비슷한 기사는 하나로 묶고, AI가 중요한 순서로 요약해 웹페이지로 만들어 줍니다.

## 사용법

- **관심 키워드 바꾸기**: `config.json`의 `keywords` 목록을 수정하면 됩니다. 이 파일만 고치면 됩니다.
- **지금 바로 갱신하기**: GitHub 저장소 → Actions 탭 → `daily-briefing` → `Run workflow` 버튼.
- **브리핑 보기**: GitHub Pages 주소로 접속 (저장소 Settings → Pages에서 확인).

## 동작 방식

1. `scripts/fetch.py` — 구글 뉴스 RSS에서 키워드별 최근 24시간 기사 수집 → `data/raw/`
2. Claude가 `scripts/summarize-prompt.md` 지시문에 따라 묶기·거르기·요약 → `data/briefings/`
3. `scripts/build.py` — 브리핑 JSON을 웹페이지로 변환 → `docs/` (GitHub Pages가 서빙)
4. `.github/workflows/daily-briefing.yml` — 위 과정을 매일 아침 자동 실행

## 로컬 테스트

```
python -m unittest discover -s tests   # 테스트 실행
python scripts/fetch.py                # 뉴스 수집
python scripts/build.py                # 페이지 생성 (data/briefings/ 필요)
```

## 관리 참고

- Claude 인증 토큰(`CLAUDE_CODE_OAUTH_TOKEN`)은 1년 유효 — 만료되면 `claude setup-token`으로 재발급 후 GitHub Secrets에 다시 등록.
