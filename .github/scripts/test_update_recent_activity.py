import unittest
from pathlib import Path
from runpy import run_path

updater = run_path(str(Path(__file__).with_name("update_recent_activity.py")))
build_lines = updater["build_lines"]
format_commit_line = updater["format_commit_line"]
format_pull_request_line = updater["format_pull_request_line"]
is_excluded_repo = updater["is_excluded_repo"]
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

    def test_format_pull_request_line(self):
        repo = "koreader/koreader"
        pr = {
            "html_url": f"https://github.com/{repo}/pull/16346",
            "title": "render visible tile when too large",
            "created_at": "2026-11-01T19:44:44Z",
        }
        line = format_pull_request_line(1, repo, 16346, pr)
        expected = "1. [`PR #16346`](https://github.com/koreader/koreader/pull/16346) - **[koreader/koreader](https://github.com/koreader/koreader)**: render visible tile when too large *(2026-11-01)*"
        self.assertEqual(line, expected)

    def test_is_excluded_repo(self):
        # Excluded repositories
        self.assertTrue(is_excluded_repo("denialbb/denialbb"))
        self.assertTrue(is_excluded_repo("DENIALBB/ZETTELKASTEN"))
        self.assertTrue(is_excluded_repo("denialbb/zettlekasten"))
        self.assertTrue(is_excluded_repo("denialbb/braindump"))
        self.assertTrue(is_excluded_repo("denialbb/dotfiles"))
        self.assertTrue(is_excluded_repo("denialbb/.dotfiles"))
        self.assertTrue(is_excluded_repo("someone/dotfiles"))
        self.assertTrue(is_excluded_repo("denialbb/nvim"))
        self.assertTrue(is_excluded_repo("denialbb/emacs"))
        self.assertTrue(is_excluded_repo("denialbb/literate-emacs"))
        self.assertTrue(is_excluded_repo("denialbb/nixos"))
        self.assertTrue(is_excluded_repo("denialbb/.agents"))
        self.assertTrue(is_excluded_repo("denialbb/qmk"))
        self.assertTrue(is_excluded_repo("denialbb/kyria"))
        self.assertTrue(is_excluded_repo("denialbb/wallpapers"))
        self.assertTrue(is_excluded_repo("denialbb/biblios"))
        self.assertTrue(is_excluded_repo("denialbb/my-system-config"))

        # Allowed repositories (third-party and public projects)
        self.assertFalse(is_excluded_repo("koreader/koreader"))
        self.assertFalse(is_excluded_repo("huacnlee/omamail"))
        self.assertFalse(is_excluded_repo("denialbb/limen"))
        self.assertFalse(is_excluded_repo("denialbb/clips-wumpus"))
        self.assertFalse(is_excluded_repo("denialbb/blinky"))
        self.assertFalse(is_excluded_repo("denialbb/kobo-notes"))
        self.assertFalse(is_excluded_repo("neovim/neovim"))

    def test_build_lines_includes_prs_and_third_party(self):
        events = [
            {
                "type": "PullRequestEvent",
                "repo": {"name": "koreader/koreader"},
                "payload": {"action": "opened", "number": 16346},
                "created_at": "2026-11-01T20:00:00Z",
            },
            {
                "type": "PushEvent",
                "repo": {"name": "denialbb/limen"},
                "payload": {"head": "0123456789abcdef0123456789abcdef01234567"},
                "created_at": "2026-11-01T19:00:00Z",
            },
        ]

        def get_commit(repo, sha):
            return {
                "commit": {"message": "feat: add feature", "author": {"date": "2026-11-01T19:00:00Z"}},
                "html_url": f"https://github.com/{repo}/commit/{sha}",
            }

        def get_pr(repo, number):
            return {
                "title": "fix: resolve memory leak",
                "created_at": "2026-11-01T20:00:00Z",
                "html_url": f"https://github.com/{repo}/pull/{number}",
                "user": {"login": "denialbb"},
            }

        lines = build_lines(events, get_commit, get_pr)
        self.assertEqual(len(lines), 2)
        self.assertIn("PR #16346", lines[0])
        self.assertIn("koreader/koreader", lines[0])
        self.assertIn("0123456", lines[1])
        self.assertIn("denialbb/limen", lines[1])

    def test_skips_excluded_and_private_repos(self):
        events = [
            {
                "type": "PushEvent",
                "repo": {"name": "denialbb/zettelkasten"},
                "payload": {"head": "1111111111111111111111111111111111111111"},
                "created_at": "2026-11-01T18:00:00Z",
            },
            {
                "type": "PushEvent",
                "repo": {"name": "denialbb/.dotfiles"},
                "payload": {"head": "2222222222222222222222222222222222222222"},
                "created_at": "2026-11-01T17:00:00Z",
            },
            {
                "type": "PushEvent",
                "repo": {"name": "denialbb/denialbb"},
                "payload": {"head": "3333333333333333333333333333333333333333"},
                "created_at": "2026-11-01T16:00:00Z",
            },
            {
                "type": "PushEvent",
                "repo": {"name": "denialbb/biblios"},
                "payload": {"head": "4444444444444444444444444444444444444444"},
                "created_at": "2026-11-01T15:00:00Z",
            },
            {
                "type": "PushEvent",
                "public": False,
                "repo": {"name": "denialbb/limen"},
                "payload": {"head": "5555555555555555555555555555555555555555"},
                "created_at": "2026-11-01T14:00:00Z",
            },
            {
                "type": "PushEvent",
                "repo": {"name": "denialbb/limen"},
                "payload": {"head": "6666666666666666666666666666666666666666"},
                "created_at": "2026-11-01T13:00:00Z",
            },
        ]

        def get_commit(repo, sha):
            return {
                "commit": {"message": "Valid commit", "author": {"date": "2026-11-01T13:00:00Z"}},
                "html_url": f"https://github.com/{repo}/commit/{sha}",
            }

        lines = build_lines(events, get_commit)
        self.assertEqual(len(lines), 1)
        self.assertIn("6666666", lines[0])

    def test_skips_prs_not_authored_by_denialbb_or_closed_unmerged(self):
        events = [
            {
                "type": "PullRequestEvent",
                "repo": {"name": "denialbb/limen"},
                "payload": {"action": "opened", "number": 10},
                "created_at": "2026-11-01T12:00:00Z",
            },
            {
                "type": "PullRequestEvent",
                "repo": {"name": "denialbb/limen"},
                "payload": {"action": "closed", "number": 11, "pull_request": {"merged": False}},
                "created_at": "2026-11-01T11:00:00Z",
            },
            {
                "type": "PullRequestEvent",
                "repo": {"name": "denialbb/limen"},
                "payload": {"action": "closed", "number": 12, "pull_request": {"merged": True}},
                "created_at": "2026-11-01T10:00:00Z",
            },
        ]

        def get_pr(repo, number):
            if number == 10:
                return {"title": "from external user", "created_at": "2026-11-01T12:00:00Z", "user": {"login": "someone_else"}}
            if number == 12:
                return {"title": "merged denialbb pr", "created_at": "2026-11-01T10:00:00Z", "user": {"login": "denialbb"}}
            return {}

        lines = build_lines(events, None, get_pr)
        self.assertEqual(len(lines), 1)
        self.assertIn("PR #12", lines[0])

    def test_deduplicates_by_sha_and_pr_number(self):
        events = [
            {
                "type": "PullRequestEvent",
                "repo": {"name": "huacnlee/omamail"},
                "payload": {"action": "merged", "number": 401, "pull_request": {"merged": True}},
                "created_at": "2026-10-25T03:00:00Z",
            },
            {
                "type": "PullRequestEvent",
                "repo": {"name": "huacnlee/omamail"},
                "payload": {"action": "opened", "number": 401},
                "created_at": "2026-10-23T17:00:00Z",
            },
        ]

        def get_pr(repo, number):
            return {"title": "credential retry", "created_at": "2026-10-23T17:00:00Z", "user": {"login": "denialbb"}}

        lines = build_lines(events, None, get_pr)
        self.assertEqual(len(lines), 1)
        self.assertIn("PR #401", lines[0])

    def test_skips_readme_update_commits(self):
        sha = "3333333333333333333333333333333333333333"
        events = [
            {"type": "PushEvent", "repo": {"name": "denialbb/limen"}, "payload": {"head": sha}},
        ]

        def get_commit(repo, sha):
            return {
                "commit": {"message": "Update README with recent activity", "author": {"date": "2026-10-15T10:00:00Z"}},
                "html_url": f"https://github.com/{repo}/commit/{sha}",
            }

        lines = build_lines(events, get_commit)
        self.assertEqual(lines, [])

    def test_replaces_only_content_between_valid_markers(self):
        content = "before\n<!--START_SECTION:activity-->\nold\n<!--END_SECTION:activity-->\nafter\n"
        self.assertEqual(
            update_readme(content, ["1. item"]),
            "before\n<!--START_SECTION:activity-->\n1. item\n<!--END_SECTION:activity-->\nafter\n",
        )

    def test_rejects_missing_or_reversed_markers(self):
        with self.assertRaises(ValueError):
            update_readme("no markers", [])
        with self.assertRaises(ValueError):
            update_readme("<!--END_SECTION:activity--><!--START_SECTION:activity-->", [])


if __name__ == "__main__":
    unittest.main()
