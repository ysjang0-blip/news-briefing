"""브리핑 JSON(data/briefings/*.json) → 정적 웹페이지(docs/) 생성.

사용법: python scripts/build.py
- 가장 최근 브리핑 → docs/index.html
- 모든 브리핑 → docs/archive/YYYY-MM-DD.html
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_IMPORTANCE_ORDER = {"상": 0, "중": 1, "하": 2}
_IMPORTANCE_CLASS = {"상": "high", "중": "mid", "하": "low"}

_CSS = """
:root { --bg:#f7f7f5; --card:#ffffff; --text:#1a1a1a; --muted:#6b6b6b; --line:#e4e4e0;
        --high:#c0392b; --mid:#b9770e; --low:#7f8c8d; --accent:#2c5f8a; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#16181c; --card:#1f2228; --text:#e8e8e6; --muted:#9a9a97; --line:#31353c;
          --high:#e57368; --mid:#d9a441; --low:#95a0a1; --accent:#7ab0d8; }
}
* { box-sizing:border-box; margin:0; padding:0; }
body { background:var(--bg); color:var(--text); font-family:'Apple SD Gothic Neo','Malgun Gothic',system-ui,sans-serif;
       line-height:1.65; padding:1rem; }
.wrap { max-width:42rem; margin:0 auto; }
header { padding:1.2rem 0 .8rem; }
header h1 { font-size:1.35rem; }
header .date { color:var(--muted); font-size:.95rem; margin-top:.15rem; }
header .byline { color:var(--muted); font-size:.78rem; letter-spacing:.04em; margin-bottom:.2rem; }
.topic { background:var(--card); border:1px solid var(--line); border-radius:12px;
         padding:1.1rem 1.2rem; margin:.9rem 0; }
.topic h2 { font-size:1.08rem; margin-bottom:.45rem; }
.badge { display:inline-block; font-size:.75rem; font-weight:700; border-radius:6px;
         padding:.1rem .45rem; margin-right:.5rem; vertical-align:2px; color:#fff; }
.badge.high { background:var(--high); } .badge.mid { background:var(--mid); } .badge.low { background:var(--low); }
.summary { font-size:.98rem; }
details { margin-top:.7rem; }
summary { color:var(--muted); font-size:.88rem; cursor:pointer; }
details a { color:var(--accent); text-decoration:none; }
details li { margin:.35rem 0 .35rem 1.2rem; font-size:.9rem; }
.src { color:var(--muted); font-size:.82rem; }
nav.archive { margin:1.6rem 0; font-size:.9rem; color:var(--muted); }
nav.archive a { color:var(--accent); text-decoration:none; margin-right:.7rem; }
footer { color:var(--muted); font-size:.8rem; margin:2rem 0 1rem; }
.empty { color:var(--muted); padding:2rem 0; }
"""


def sort_topics(topics):
    """중요도 상→중→하 순 정렬. 알 수 없는 값은 맨 뒤."""
    return sorted(topics, key=lambda t: _IMPORTANCE_ORDER.get(t.get("importance"), 99))


def _render_topic(topic):
    e = html.escape
    importance = topic.get("importance", "중")
    badge_class = _IMPORTANCE_CLASS.get(importance, "mid")
    articles = topic.get("articles", [])
    links = "\n".join(
        f'<li><a href="{e(a.get("link", ""))}" target="_blank" rel="noopener">{e(a.get("title", ""))}</a>'
        f' <span class="src">{e(a.get("source", ""))}</span></li>'
        for a in articles
    )
    sources = f"""
  <details>
    <summary>관련 기사 {len(articles)}건 · 원문 보기</summary>
    <ul>{links}</ul>
  </details>""" if articles else ""
    return f"""<article class="topic">
  <h2><span class="badge {badge_class}">{e(importance)}</span>{e(topic.get("title", ""))}</h2>
  <p class="summary">{e(topic.get("summary", ""))}</p>{sources}
</article>"""


def render_page(briefing, archive_dates, base=""):
    """브리핑 하나 → 완성된 HTML 페이지 문자열.

    base: 링크 앞에 붙일 경로 접두어 (index는 "", archive 페이지는 "../")
    """
    e = html.escape
    date = briefing.get("date", "")
    topics = sort_topics(briefing.get("topics", []))
    body = "\n".join(_render_topic(t) for t in topics) if topics else '<p class="empty">오늘은 표시할 뉴스가 없습니다.</p>'
    other_dates = [d for d in archive_dates if d != date]
    archive_links = " ".join(
        f'<a href="{base}archive/{e(d)}.html">{e(d)}</a>' for d in sorted(other_dates, reverse=True)[:14]
    )
    archive_nav = f'<nav class="archive">지난 브리핑: {archive_links}</nav>' if archive_links else ""
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>아침 뉴스 브리핑 · {e(date)}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
<header>
  <p class="byline">장용석의 뉴스요약</p>
  <h1>&#9749; 아침 뉴스 브리핑</h1>
  <p class="date">{e(date)} · 비슷한 뉴스는 하나로 묶고, 중요한 순서로 정리했습니다.</p>
</header>
<main>
{body}
</main>
{archive_nav}
<footer>구글 뉴스에서 수집한 기사를 AI가 요약했습니다. 정확한 내용은 원문 기사를 확인하세요.</footer>
</div>
</body>
</html>"""


def load_briefings(briefing_dir):
    """폴더의 브리핑 JSON을 날짜순으로 읽는다. 깨진 파일은 경고만 남기고 건너뛴다."""
    import sys
    briefings = []
    for f in sorted(briefing_dir.glob("*.json")):
        try:
            briefings.append(json.loads(f.read_text(encoding="utf-8")))
        except json.JSONDecodeError as e:
            print(f"[warn] {f.name} 이 올바른 JSON이 아니라 건너뜁니다: {e}", file=sys.stderr)
    return briefings


def main():
    briefings = load_briefings(ROOT / "data" / "briefings")
    if not briefings:
        raise SystemExit("data/briefings/ 에 읽을 수 있는 브리핑 JSON이 없습니다. 요약 단계를 먼저 실행하세요.")

    dates = [b.get("date", "") for b in briefings]
    docs = ROOT / "docs"
    (docs / "archive").mkdir(parents=True, exist_ok=True)

    for briefing in briefings:
        page = render_page(briefing, archive_dates=dates, base="../")
        # archive 페이지의 archive/ 링크는 같은 폴더 안이므로 접두어를 정리한다
        page = page.replace('href="../archive/', 'href="')
        (docs / "archive" / f"{briefing.get('date', '')}.html").write_text(page, encoding="utf-8")

    latest = briefings[-1]
    (docs / "index.html").write_text(render_page(latest, archive_dates=dates), encoding="utf-8")
    print(f"[info] index.html (최신: {latest.get('date', '')}) + 아카이브 {len(dates)}개 생성 완료")


if __name__ == "__main__":
    main()
