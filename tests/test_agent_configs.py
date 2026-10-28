"""Every agent that opens the repo gets the same Keel.

Keel ships one config file per agent, because each agent reads its own: the MCP server
from `.mcp.json`, `.codex/config.toml`, `.cursor/mcp.json` and the rest, and the skills
from `.agents/skills/` (the shared location) or `.claude/skills/` (Claude Code only).
Copies drift silently: a skill fixed in one folder and not the other, or a launch command
changed in one file, works in the agent you happened to test and breaks in the others.
"""
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMMAND = ["python", "-m", "keel.mcp.server"]


def _skill_files(folder: Path) -> dict[str, bytes]:
    # Line endings are normalised: a Windows checkout may write CRLF where git stores LF.
    return {
        p.relative_to(folder).as_posix(): p.read_bytes().replace(b"\r\n", b"\n")
        for p in sorted(folder.rglob("*")) if p.is_file() and "__pycache__" not in p.parts
    }


def test_skills_are_the_same_in_both_folders():
    shared = _skill_files(ROOT / ".agents" / "skills")
    claude = _skill_files(ROOT / ".claude" / "skills")
    assert shared, ".agents/skills is empty"
    only = sorted(set(shared) ^ set(claude))
    differ = sorted(k for k in set(shared) & set(claude) if shared[k] != claude[k])
    assert not only and not differ, (
        "the skill folders drifted; copy the edited file across. "
        f"In one folder only: {only}. Different: {differ}"
    )


def _mcp_servers_entry(path: str) -> list[str]:
    entry = json.loads((ROOT / path).read_text(encoding="utf-8"))["mcpServers"]["keel"]
    return [entry["command"], *entry["args"]]


def _mcp_entry(path: str) -> list[str]:
    # OpenCode and Kilo Code take the command as one array. kilo.jsonc carries no
    # comments, so it parses as plain JSON.
    return json.loads((ROOT / path).read_text(encoding="utf-8"))["mcp"]["keel"]["command"]


def _codex_entry() -> list[str]:
    entry = tomllib.loads((ROOT / ".codex" / "config.toml").read_text(encoding="utf-8"))
    server = entry["mcp_servers"]["keel"]
    return [server["command"], *server["args"]]


def test_every_agent_launches_the_same_server():
    launches = {
        ".mcp.json": _mcp_servers_entry(".mcp.json"),
        ".cursor/mcp.json": _mcp_servers_entry(".cursor/mcp.json"),
        ".gemini/settings.json": _mcp_servers_entry(".gemini/settings.json"),
        "opencode.json": _mcp_entry("opencode.json"),
        ".kilo/kilo.jsonc": _mcp_entry(".kilo/kilo.jsonc"),
        ".codex/config.toml": _codex_entry(),
    }
    wrong = {path: cmd for path, cmd in launches.items() if cmd != COMMAND}
    assert not wrong, f"these configs launch something other than {COMMAND}: {wrong}"
