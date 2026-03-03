import os

import click
import dotenv

dotenv.load_dotenv()


@click.command()
@click.option(
    "--access-key-id",
    type=str,
    help="Alibaba Cloud AccessKey ID (env: ALIBABA_CLOUD_ACCESS_KEY_ID)",
    default=None,
)
@click.option(
    "--access-key-secret",
    type=str,
    help="Alibaba Cloud AccessKey Secret (env: ALIBABA_CLOUD_ACCESS_KEY_SECRET)",
    default=None,
)
@click.option(
    "--region-id",
    type=str,
    help="Alibaba Cloud region ID",
    default="cn-hangzhou",
    show_default=True,
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
    """
    from mcp_server_agentloop_memory.server import run_server

    ak_id = access_key_id or os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID")
    ak_secret = access_key_secret or os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
    ws = workspace or os.getenv("ALIBABA_CLOUD_WORKSPACE")
    ms = memory_store or os.getenv("ALIBABA_CLOUD_MEMORY_STORE")

    if not ak_id or not ak_secret:
        raise click.UsageError(
            "AccessKey credentials required. Use --access-key-id/--access-key-secret "
            "or set ALIBABA_CLOUD_ACCESS_KEY_ID/ALIBABA_CLOUD_ACCESS_KEY_SECRET env vars."
        )
    if not ws:
        raise click.UsageError(
            "Workspace required. Use --workspace or set ALIBABA_CLOUD_WORKSPACE env var."
        )
    if not ms:
        raise click.UsageError(
            "Memory store required. Use --memory-store or set ALIBABA_CLOUD_MEMORY_STORE env var."
        )

    run_server(
        access_key_id=ak_id,
        access_key_secret=ak_secret,
        region_id=region_id,
        workspace=ws,
        memory_store=ms,
        host=host,
        port=port,
        log_level=log_level,
    )
