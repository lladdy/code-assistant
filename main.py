import asyncio


import subprocess
import boto3
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.providers.bedrock import BedrockProvider
from botocore.config import Config as BotocoreConfig

bedrock_config = BotocoreConfig(
    read_timeout=300,
    connect_timeout=60,
    retries={"max_attempts": 3},
)
bedrock_client = boto3.client(
    "bedrock-runtime", region_name="eu-central-1", config=bedrock_config
)
model = BedrockConverseModel(
    "eu.anthropic.claude-sonnet-4-20250514-v1:0",
    provider=BedrockProvider(bedrock_client=bedrock_client),
)


instructions = """
You are a specialised agent for maintaining and developing the XXXXXX codebase.

## Development Guidelines:

1. **Test Failures:**
   - When tests fail, fix the implementation first, not the tests
   - Tests represent expected behavior; implementation should conform to tests
   - Only modify tests if they clearly don't match specifications

2. **Code Changes:**
   - Make the smallest possible changes to fix issues
   - Focus on fixing the specific problem rather than rewriting large portions
   - Add unit tests for all new functionality before implementing it

3. **Best Practices:**
   - Keep functions small with a single responsibility
   - Implement proper error handling with appropriate exceptions
   - Be mindful of configuration dependencies in tests

Remember to examine test failure messages carefully to understand the root cause before making any changes.
"""


run_python = MCPServerStdio(
    "deno",
    args=[
        "run",
        "-N",
        "-R=node_modules",
        "-W=node_modules",
        "--node-modules-dir=auto",
        "jsr:@pydantic/mcp-run-python",
        "stdio",
    ],
)

internet_search = MCPServerStdio(command="uvx", args=["duckduckgo-mcp-server"])
code_reasoning = MCPServerStdio(
    command="npx",
    args=["-y", "@mettamatt/code-reasoning"],
    tool_prefix="code_reasoning",
)
desktop_commander = MCPServerStdio(
    command="npx",
    args=["-y", "@wonderwhy-er/desktop-commander"],
    tool_prefix="desktop_commander",
)
awslabs = MCPServerStdio(
    command="uvx",
    args=["awslabs.core-mcp-server@latest"],
    env={"FASTMCP_LOG_LEVEL": "ERROR"},
    tool_prefix="awslabs",
)
aws_docs = MCPServerStdio(
    command="uvx",
    args=["awslabs.aws-documentation-mcp-server@latest"],
    env={"FASTMCP_LOG_LEVEL": "ERROR", "AWS_DOCUMENTATION_PARTITION": "aws"},
    tool_prefix="aws_docs",
)
context7 = MCPServerStdio(
    command="npx", args=["-y", "@upstash/context7-mcp"], tool_prefix="context"
)

agent = Agent(
    instructions=instructions,
    model=model,
    mcp_servers=[
        run_python,
        internet_search,
        code_reasoning,
        context7,
        awslabs,
        aws_docs,
        desktop_commander,
    ],
)


@agent.tool_plain()
def run_unit_tests() -> str:
    """Run unit tests using uv."""
    result = subprocess.run(
        ["uv", "run", "pytest", "-xvs", "tests/"], capture_output=True, text=True
    )
    return result.stdout


async def main():
    async with agent.run_mcp_servers():
        await agent.to_cli()


if __name__ == "__main__":
    asyncio.run(main())