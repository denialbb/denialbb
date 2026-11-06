import json
import re
import subprocess
import sys
from pathlib import Path

START = "<!--START_SECTION:activity-->"
END = "<!--END_SECTION:activity-->"
EVENTS_ENDPOINT = "users/denialbb/events/public?per_page=100"
MAX_ITEMS = 5

EXCLUDED_EXACT_REPOS = {
    # Profile & personal notes
    "denialbb/denialbb",
    "denialbb/zettelkasten",
    "denialbb/zettlekasten",
    "denialbb/braindump",
    "denialbb/cortex",
    # Dotfiles & personal configs
    "denialbb/dotfiles",
    "denialbb/.dotfiles",
    "denialbb/nvim",
    "denialbb/emacs",
    "denialbb/literate-emacs",
    "denialbb/nixos",
    "denialbb/.agents",
    "denialbb/qmk",
    "denialbb/kyria",
    "denialbb/wallpapers",
    # Known private repos
    "denialbb/biblios",
    "denialbb/batch-scheduling",
    "denialbb/ai-2526",
    "denialbb/tensorhci",
    "denialbb/all-cast",
    "denialbb/eliva26-ink-detection",
    "denialbb/ai-tooling",
    "denialbb/agent-skills",
    "denialbb/eliva26-industrial-vision",
    "denialbb/eliva26-restoration",
    "denialbb/raylib-assets",
    "denialbb/journal",
    "denialbb/endlessrun",
    "denialbb/pstore",
}

EXCLUDED_NAME_PATTERNS = {
    "denialbb",
    "zettelkasten",
    "zettlekasten",
    "braindump",
    "cortex",
    "dotfiles",
    ".dotfiles",
    "nvim",
    "emacs",
    "literate-emacs",
    "nixos",
    ".agents",
    "qmk",
    "kyria",
    "wallpapers",
}


def is_excluded_repo(repo: str) -> bool:
    repo_lower = repo.lower().strip()
    if repo_lower in EXCLUDED_EXACT_REPOS:
        return True

    parts = repo_lower.split("/")
    owner = parts[0] if len(parts) > 1 else ""
    name = parts[-1] if parts else repo_lower

    if name in ("dotfiles", ".dotfiles") or name.endswith("-dotfiles") or name.endswith(".dotfiles"):
        return True

    if owner == "denialbb":
        if name in EXCLUDED_NAME_PATTERNS:
            return True
        if "config" in name or "dotfile" in name or name.endswith("-setup"):
            return True

    return False


def get_json(endpoint: str):
    try:
        result = subprocess.run(
            ["gh", "api", endpoint],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        raise RuntimeError(f"GitHub API request failed: {endpoint}") from error


def get_commit(repo: str, sha: str):
    return get_json(f"repos/{repo}/commits/{sha}")


def get_pull_request(repo: str, number: int):
    return get_json(f"repos/{repo}/pulls/{number}")


def format_commit_line(index: int, repo: str, sha: str, commit: dict, fallback_date: str = "") -> str:
    short_sha = sha[:7]
    commit_url = commit.get("html_url") or f"https://github.com/{repo}/commit/{sha}"
    repo_url = f"https://github.com/{repo}"

    commit_data = commit.get("commit", {})
    message = commit_data.get("message", "").splitlines()
    summary = message[0].strip() if message else ""
    summary = summary.replace("<", "&lt;").replace(">", "&gt;")

    date_str = (
        commit_data.get("author", {}).get("date")
        or commit_data.get("committer", {}).get("date")
        or fallback_date
    )
    date = date_str[:10] if date_str else ""
    date_part = f" *({date})*" if date else ""
    return f"{index}. [`{short_sha}`]({commit_url}) - **[{repo}]({repo_url})**: {summary}{date_part}"


def format_pull_request_line(index: int, repo: str, number: int, pr: dict, fallback_date: str = "") -> str:
    pr_url = pr.get("html_url") or f"https://github.com/{repo}/pull/{number}"
    repo_url = f"https://github.com/{repo}"

    title = pr.get("title", "").strip()
    title = title.replace("<", "&lt;").replace(">", "&gt;")

    date_str = pr.get("created_at") or fallback_date
    date = date_str[:10] if date_str else ""
    date_part = f" *({date})*" if date else ""
    return f"{index}. [`PR #{number}`]({pr_url}) - **[{repo}]({repo_url})**: {title}{date_part}"


def build_lines(events, fetch_commit, fetch_pull_request=None, max_items=MAX_ITEMS):
    if fetch_pull_request is None:
        fetch_pull_request = get_pull_request

    sorted_events = sorted(events, key=lambda e: e.get("created_at", ""), reverse=True)
    lines = []
    seen_keys = set()
    seen_summaries = set()

    for event in sorted_events:
        if event.get("public") is False:
            continue
        repo = event.get("repo", {}).get("name", "")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            continue
        if is_excluded_repo(repo):
            continue

        etype = event.get("type")
        fallback_date = event.get("created_at", "")

        if etype == "PushEvent":
            sha = event.get("payload", {}).get("head", "")
            if not re.fullmatch(r"[0-9a-fA-F]{40}", sha):
                continue
            key = f"commit:{sha}"
            if key in seen_keys:
                continue
            seen_keys.add(key)

            try:
                commit = fetch_commit(repo, sha)
            except Exception as e:
                print(f"Warning: Failed to fetch commit {sha} from {repo}: {e}", file=sys.stderr)
                continue

            if commit.get("private") or commit.get("repository", {}).get("private"):
                continue

            commit_message = commit.get("commit", {}).get("message", "")
            if commit_message.startswith("Update README"):
                continue

            message_lines = commit_message.splitlines()
            summary = message_lines[0].strip() if message_lines else ""
            if not summary:
                continue

            summary_key = (repo.lower(), summary)
            if summary_key in seen_summaries:
                continue
            seen_summaries.add(summary_key)

            line = format_commit_line(len(lines) + 1, repo, sha, commit, fallback_date=fallback_date)
            lines.append(line)

        elif etype == "PullRequestEvent":
            action = event.get("payload", {}).get("action", "")
            is_merged = event.get("payload", {}).get("pull_request", {}).get("merged", False)
            if action not in ("opened", "reopened", "merged") and not (action == "closed" and is_merged):
                continue

            number = event.get("payload", {}).get("number")
            if not number:
                continue

            key = f"pr:{repo.lower()}#{number}"
            if key in seen_keys:
                continue
            seen_keys.add(key)

            try:
                pr = fetch_pull_request(repo, number)
            except Exception as e:
                print(f"Warning: Failed to fetch pull request #{number} from {repo}: {e}", file=sys.stderr)
                continue

            if pr.get("private") or pr.get("base", {}).get("repo", {}).get("private"):
                continue

            author = pr.get("user", {}).get("login", "")
            if author and author.lower() != "denialbb":
                continue

            title = pr.get("title", "").strip()
            if not title:
                continue

            summary_key = (repo.lower(), title)
            if summary_key in seen_summaries:
                continue
            seen_summaries.add(summary_key)

            line = format_pull_request_line(len(lines) + 1, repo, number, pr, fallback_date=fallback_date)
            lines.append(line)

        if len(lines) >= max_items:
            break

    return lines


def update_readme(content: str, lines: list) -> str:
    start = content.find(START)
    end = content.find(END)
    if start < 0 or end < 0 or end < start:
        raise ValueError("README activity markers are missing or out of order")
    return content[:start + len(START)] + "\n" + "\n".join(lines) + "\n" + content[end:]


def main():
    try:
        events = get_json(EVENTS_ENDPOINT)
    except Exception as e:
        print(f"Error fetching public events: {e}", file=sys.stderr)
        sys.exit(1)

    lines = build_lines(events, get_commit, get_pull_request)
    if not lines:
        print("No public activity found; leaving README unchanged.")
        return

    readme = Path("README.md")
    updated = update_readme(readme.read_text(), lines)
    readme.write_text(updated)
    print(f"Successfully updated README.md with {len(lines)} recent activities.")


if __name__ == "__main__":
    main()
