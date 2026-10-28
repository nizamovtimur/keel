"""`python -m keel [up|down|validate|schema|style-guide|--http]` - the CLI entry point."""
import sys

# `up` runs at the start of every session, so it does not pay for importing the MCP SDK
# it never uses.
if len(sys.argv) > 1 and sys.argv[1] in ("up", "down"):
    from keel.up import main
else:
    from keel.mcp.server import main

main()
