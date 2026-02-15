import mcp.client.stdio
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

from mcp.types import (
    Tool,
    Resource,
    Prompt,
    ListToolsResult,
    ListResourcesResult,
    ReadResourceResult,
    CallToolResult,
)

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="pixi",  # Executable
    args=[
        "run",
        "python",
        "src/talewind/mcp_servers/inventory/server.py",
    ],  # Optional command line arguments
    env=None,  # Optional environment variables
)


class McpFacade:
    def __init__(self):
        pass

    async def list_resources(self) -> ListResourcesResult:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write, sampling_callback=None) as session:
                # Initialize the connection
                await session.initialize()

                # List available resources
                return await session.list_resources()

    async def list_tools(self) -> ListToolsResult:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write, sampling_callback=None) as session:
                # Initialize the connection
                await session.initialize()

                # List available tools
                return await session.list_tools()

    async def read_resource(self, uri) -> ReadResourceResult:
        """
        Call a tool with the given name and arguments.
        """
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write, sampling_callback=None) as session:
                # Initialize the connection
                await session.initialize()

                # Call a tool
                return await session.read_resource(uri)

    async def call_tool(self, tool_name: str, arguments: dict) -> CallToolResult:
        """
        Call a tool with the given name and arguments.
        """
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write, sampling_callback=None) as session:
                # Initialize the connection
                await session.initialize()

                # Call a tool
                return await session.call_tool(tool_name, arguments=arguments)
