"""scripts/build.py 의 HTML 생성 로직 테스트."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build import render_page, sort_topics, load_briefings

BRIEFING = {
    "date": "2026-08-15",
    "topics": [
        {
            "title": "코스피 사상 최고",
            "summary": "코스피가 사상 최고치를 경신했다.",
            "importance": "중",
            "articles": [
                {"title": "코스피 신기록 - 연합뉴스", "link": "https://x/2", "source": "연합뉴스"},
            ],
        },
        {
            "title": "한은 기준금리 동결",
            "summary": "한국은행이 기준금리를 동결했다. 시장은 안도했다.",
            "importance": "상",
            "articles": [
                {"title": "한은 동결 - 한국경제", "link": "https://x/1", "source": "한국경제"},
                {"title": "금리 동결 - 매경", "link": "https://x/3", "source": "매일경제"},
            ],
        },
    ],
}


class TestSortTopics(unittest.TestCase):
    def test_sorts_by_importance_high_first(self):
        topics = sort_topics(BRIEFING["topics"])
        self.assertEqual([t["importance"] for t in topics], ["상", "중"])

    def test_unknown_importance_goes_last(self):
        topics = sort_topics([
            {"importance": "??", "title": "a"},
            {"importance": "하", "title": "b"},
        ])
        self.assertEqual([t["title"] for t in topics], ["b", "a"])


class TestRenderPage(unittest.TestCase):
    def test_contains_topic_title_summary_and_links(self):
        html = render_page(BRIEFING, archive_dates=["2026-08-15", "2026-08-14"])
        self.assertIn("한은 기준금리 동결", html)
        self.assertIn("시장은 안도했다", html)
        self.assertIn('href="https://x/1"', html)
        self.assertIn("한국경제", html)

    def test_shows_related_article_count(self):
        html = render_page(BRIEFING, archive_dates=[])
        self.assertIn("관련 기사 2", html)

    def test_escapes_html_in_content(self):
        briefing = {
            "date": "2026-08-15",
            "topics": [{
                "title": "<script>alert(1)</script>",
                "summary": "s",
                "importance": "상",
                "articles": [],
            }],
        }
        html = render_page(briefing, archive_dates=[])
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_archive_links_to_other_dates(self):
        html = render_page(BRIEFING, archive_dates=["2026-08-15", "2026-08-14"])
        self.assertIn('archive/2026-08-14.html', html)


class TestLoadBriefings(unittest.TestCase):
    def test_skips_invalid_json_and_keeps_valid(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "2026-09-02.json"
            good.write_text(json.dumps(BRIEFING, ensure_ascii=False), encoding="utf-8")
            bad = Path(tmp) / "2026-09-03.json"
            bad.write_text('{"date": "2026-09-03", "topics": [{"title": "잘못된 "따옴표""}]}', encoding="utf-8")
            briefings = load_briefings(Path(tmp))
        # 깨진 파일은 건너뛰고, 정상 파일만 (날짜순으로) 남아야 한다
        self.assertEqual([b["date"] for b in briefings], ["2026-08-15"])


if __name__ == "__main__":
    unittest.main()
