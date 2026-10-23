import unittest
from pathlib import Path
from runpy import run_path

updater = run_path(str(Path(__file__).with_name("update_recent_activity.py")))
build_lines = updater["build_lines"]
format_commit_line = updater["format_commit_line"]
update_readme = updater["update_readme"]


class UpdateRecentActivityTests(unittest.TestCase):
    def test_format_commit_line(self):
        sha = "0123456789abcdef0123456789abcdef01234567"
        repo = "denialbb/project"
        commit = {
            "html_url": f"https://github.com/{repo}/commit/{sha}",
            "commit": {
                "message": "fix: bug fix\n\nExtra details",
                "author": {"date": "2026-10-16T12:00:00Z"},
            },
        }
        line = format_commit_line(1, repo, sha, commit)
        expected = "1. [`0123456`](https://github.com/denialbb/project/commit/0123456789abcdef0123456789abcdef01234567) - **[denialbb/project](https://github.com/denialbb/project)**: fix: bug fix *(2026-10-16)*"
        self.assertEqual(line, expected)

    def test_uses_commit_endpoint_for_push_head_and_skips_duplicate_sha(self):
        sha = "0123456789abcdef0123456789abcdef01234567"
        events = [
            {"type": "PushEvent", "repo": {"name": "denialbb/project"}, "payload": {"head": sha}},
            {"type": "PushEvent", "repo": {"name": "denialbb/project"}, "payload": {"head": sha}},
        ]
        calls = []

        def get_commit(repo, sha):
            calls.append((repo, sha))
            return {
                "commit": {
                    "message": "Fix issue\nDetails",
                    "author": {"date": "2026-10-16T15:30:00Z"},
                },
                "html_url": f"https://github.com/denialbb/project/commit/{sha}",
            }

        lines = build_lines(events, get_commit)
        expected_line = f"1. [`0123456`](https://github.com/denialbb/project/commit/{sha}) - **[denialbb/project](https://github.com/denialbb/project)**: Fix issue *(2026-10-16)*"
        self.assertEqual(lines, [expected_line])
        self.assertEqual(calls, [("denialbb/project", "0123456789abcdef0123456789abcdef01234567")])

    def test_skips_failed_fetch_commit(self):
        sha1 = "1111111111111111111111111111111111111111"
        sha2 = "2222222222222222222222222222222222222222"
        events = [
            {"type": "PushEvent", "repo": {"name": "denialbb/p1"}, "payload": {"head": sha1}},
            {"type": "PushEvent", "repo": {"name": "denialbb/p2"}, "payload": {"head": sha2}},
        ]

        def get_commit(repo, sha):
            if sha == sha1:
                raise RuntimeError("API error")
            return {
                "commit": {"message": "Success", "author": {"date": "2026-10-15T10:00:00Z"}},
                "html_url": f"https://github.com/{repo}/commit/{sha}",
            }

        lines = build_lines(events, get_commit)
        self.assertEqual(len(lines), 1)
        self.assertIn("denialbb/p2", lines[0])

    def test_skips_readme_update_commits(self):
        sha = "3333333333333333333333333333333333333333"
        events = [
            {"type": "PushEvent", "repo": {"name": "denialbb/denialbb"}, "payload": {"head": sha}},
        ]

        def get_commit(repo, sha):
            return {
                "commit": {"message": "Update README with recent commits", "author": {"date": "2026-10-15T10:00:00Z"}},
                "html_url": f"https://github.com/{repo}/commit/{sha}",
            }

        lines = build_lines(events, get_commit)
        self.assertEqual(lines, [])

    def test_replaces_only_content_between_valid_markers(self):
        content = "before\n<!--START_SECTION:activity-->\nold\n<!--END_SECTION:activity-->\nafter\n"
        self.assertEqual(
            update_readme(content, ["1. commit"]),
            "before\n<!--START_SECTION:activity-->\n1. commit\n<!--END_SECTION:activity-->\nafter\n",
        )

    def test_rejects_missing_or_reversed_markers(self):
        with self.assertRaises(ValueError):
            update_readme("no markers", [])
        with self.assertRaises(ValueError):
            update_readme("<!--END_SECTION:activity--><!--START_SECTION:activity-->", [])


if __name__ == "__main__":
    unittest.main()
