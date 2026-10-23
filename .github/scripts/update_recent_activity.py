import json
import re
import subprocess
import sys
from pathlib import Path

START = "<!--START_SECTION:activity-->"
END = "<!--END_SECTION:activity-->"
EVENTS_ENDPOINT = "users/denialbb/events/public"
MAX_COMMITS = 5


def get_json(endpoint):
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


def get_commit(repo, sha):
    return get_json(f"repos/{repo}/commits/{sha}")


def format_commit_line(index, repo, sha, commit, fallback_date=""):
    short_sha = sha[:7]
    commit_url = commit.get("html_url") or f"https://github.com/{repo}/commit/{sha}"
    repo_url = f"https://github.com/{repo}"
    
    commit_data = commit.get("commit", {})
    message = commit_data.get("message", "").splitlines()
    summary = message[0].strip() if message else ""
    # Escape pipe or HTML tags if needed, but summary is outside links
    summary = summary.replace("<", "&lt;").replace(">", "&gt;")
    
    date_str = (
        commit_data.get("author", {}).get("date")
        or commit_data.get("committer", {}).get("date")
        or fallback_date
    )
    date = date_str[:10] if date_str else ""
    
    date_part = f" *({date})*" if date else ""
    return f"{index}. [`{short_sha}`]({commit_url}) - **[{repo}]({repo_url})**: {summary}{date_part}"


def build_lines(events, fetch_commit, max_commits=MAX_COMMITS):
    lines = []
    seen = set()
    for event in events:
        if event.get("type") != "PushEvent":
            continue
        repo = event.get("repo", {}).get("name", "")
        sha = event.get("payload", {}).get("head", "")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            continue
        if not re.fullmatch(r"[0-9a-fA-F]{40}", sha) or sha in seen:
            continue
        seen.add(sha)
        
        try:
            commit = fetch_commit(repo, sha)
        except Exception as e:
            print(f"Warning: Failed to fetch commit {sha} from {repo}: {e}", file=sys.stderr)
            continue
            
        commit_message = commit.get("commit", {}).get("message", "")
        # Skip automated README update commits
        if commit_message.startswith("Update README"):
            continue
            
        fallback_date = event.get("created_at", "")
        line = format_commit_line(len(lines) + 1, repo, sha, commit, fallback_date=fallback_date)
        lines.append(line)
        if len(lines) >= max_commits:
            break
            
    return lines


def update_readme(content, lines):
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

    lines = build_lines(events, get_commit)
    if not lines:
        print("No public commits found; leaving README unchanged.")
        return

    readme = Path("README.md")
    updated = update_readme(readme.read_text(), lines)
    readme.write_text(updated)
    print(f"Successfully updated README.md with {len(lines)} recent commits.")


if __name__ == "__main__":
    main()
