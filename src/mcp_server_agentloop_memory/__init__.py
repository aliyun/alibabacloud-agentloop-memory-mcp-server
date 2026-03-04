import os

import click
import dotenv

dotenv.load_dotenv()


@click.command()
@click.option(
    "--access-key-id",
    type=str,
    help="Alibaba Cloud AccessKey ID. "
    "If not provided, credentials are resolved via the default credential chain "
    "(env vars, OIDC, config file, ECS RAM role, etc.).",
    default=None,
)
@click.option(
    "--access-key-secret",
    type=str,
    help="Alibaba Cloud AccessKey Secret. Must be used together with --access-key-id.",
    default=None,
)
@click.option(
    "--region-id",
    type=str,
    help="Alibaba Cloud region ID (env: ALIBABA_CLOUD_REGION_ID)",
    default=None,
)
@click.option(
    "--workspace",
    type=str,
    help="CMS workspace name (env: ALIBABA_CLOUD_WORKSPACE)",
    default=None,
)
@click.option(
    "--memory-store",
    type=str,
    help="Memory store name (env: ALIBABA_CLOUD_MEMORY_STORE)",
    default=None,
)
@click.option(
    "--host",
    type=str,
    help="Server host",
    default="0.0.0.0",
    show_default=True,
)
@click.option(
    "--port",
    type=int,
    help="Server port",
    default=8765,
    show_default=True,
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    help="Log level",
    default="INFO",
    show_default=True,
)
def main(
    access_key_id,
    access_key_secret,
    region_id,
    workspace,
    memory_store,
    host,
    port,
    log_level,
):
    """Alibaba Cloud AgentLoop Memory MCP Server

    Provides memory management tools via MCP protocol over SSE transport.
    Connect at: GET /mcp/{client_name}/sse/{user_id}

    Credential resolution order:

    \b
      1. CLI args --access-key-id / --access-key-secret (highest priority)
      2. RAM Role ARN (env ALIBABA_CLOUD_ROLE_ARN + AK/SK env vars)
      3. Default credential chain (env AK/SK, OIDC, config file, ECS RAM role, etc.)
    """
    from mcp_server_agentloop_memory.server import run_server

    region = region_id or os.getenv("ALIBABA_CLOUD_REGION_ID", "cn-hangzhou")
    ws = workspace or os.getenv("ALIBABA_CLOUD_WORKSPACE")
    ms = memory_store or os.getenv("ALIBABA_CLOUD_MEMORY_STORE")

    if not ws:
        raise click.UsageError(
            "Workspace required. Use --workspace or set ALIBABA_CLOUD_WORKSPACE env var."
        )
    if not ms:
        raise click.UsageError(
            "Memory store required. Use --memory-store or set ALIBABA_CLOUD_MEMORY_STORE env var."
        )

    run_server(
        region_id=region,
        workspace=ws,
        memory_store=ms,
        access_key_id=access_key_id,
        access_key_secret=access_key_secret,
        host=host,
        port=port,
        log_level=log_level,
    )
