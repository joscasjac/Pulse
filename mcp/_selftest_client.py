"""Dev helper: connect to the Pulse MCP server the same way Claude does
(spawn over stdio → initialize → list tools). Proves the connection works.

Run:  .venv/bin/python _selftest_client.py
"""

import asyncio
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = os.path.dirname(os.path.abspath(__file__))


async def main():
    # Pass only the current env — let the server read creds from .pulse.env.
    params = StdioServerParameters(
        command=os.path.join(HERE, ".venv/bin/python"),
        args=[os.path.join(HERE, "pulse_mcp_server.py")],
        env={**os.environ},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            info = await session.initialize()
            print(f"HANDSHAKE OK  server='{info.serverInfo.name}' protocol={info.protocolVersion}")
            tools = await session.list_tools()
            print(f"TOOLS DISCOVERED: {len(tools.tools)}")
            for t in tools.tools:
                print(f"  - {t.name}")

            # Live call through the whole chain (server authenticates via .pulse.env).
            res = await session.call_tool("list_projects", {})
            print("LIVE call_tool list_projects ->")
            print(res.content[0].text[:600])


if __name__ == "__main__":
    asyncio.run(main())
