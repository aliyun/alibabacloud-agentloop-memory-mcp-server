"""
AgentLoop Memory MCP Server

Based on alibabacloud_cms20240330 SDK. Provides 5 memory management tools
over SSE transport with user_id / client_name injected via URL path.

SSE endpoint: GET /mcp/{client_name}/sse/{user_id}
"""

import asyncio
import contextvars
import json
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, Request

load_dotenv()
from fastapi.routing import APIRouter
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport

from typing import Optional

from alibabacloud_cms20240330.client import Client as CmsClient
from alibabacloud_cms20240330 import models as cms_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_credentials.client import Client as CredClient
from alibabacloud_credentials.models import Config as CredConfig
from alibabacloud_credentials.utils import auth_util

from mcp_server_agentloop_memory.config import (
    READ_TIMEOUT_MS,
    CONNECT_TIMEOUT_MS,
    cms_endpoint,
)

logger = logging.getLogger(__name__)


def _create_cms_config(
    access_key_id: Optional[str] = None,
    access_key_secret: Optional[str] = None,
) -> open_api_models.Config:
    """Create an OpenAPI config with unified credential resolution.

    Resolution order:
      1. CLI-provided AK/SK (only when both are explicitly passed via command-line args).
      2. RAM Role ARN (env ALIBABA_CLOUD_ROLE_ARN + AK/SK env vars → STS AssumeRole).
      3. Default credential chain handled by alibabacloud-credentials SDK:
         env AK/SK → OIDC → config file → ECS RAM role → credentials URI.
    """
    if access_key_id and access_key_secret:
        logger.info("Credential: using CLI-provided AK/SK")
        return open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
        )

    if auth_util.environment_role_arn:
        logger.info(f"Credential: using Role-ARN {auth_util.environment_role_arn}")
        credentials_client = CredClient(
            CredConfig(
                type="ram_role_arn",
                access_key_id=auth_util.environment_access_key_id,
                access_key_secret=auth_util.environment_access_key_secret,
                role_arn=auth_util.environment_role_arn,
                role_session_name=auth_util.environment_role_session_name,
            )
        )
        return open_api_models.Config(credential=credentials_client)

    logger.info("Credential: using default credential chain")
    credentials_client = CredClient()
    return open_api_models.Config(credential=credentials_client)


# ---------------------------------------------------------------------------
# Module-level state – populated by run_server()
# ---------------------------------------------------------------------------
_cms_client: CmsClient | None = None
_workspace: str = ""
_memory_store: str = ""

# Context variables – set per SSE connection from URL path
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("user_id")
client_name_var: contextvars.ContextVar[str] = contextvars.ContextVar("client_name")

mcp = FastMCP("agentloop-memory-mcp-server")


def _runtime() -> util_models.RuntimeOptions:
    rt = util_models.RuntimeOptions()
    rt.read_timeout = READ_TIMEOUT_MS
    rt.connect_timeout = CONNECT_TIMEOUT_MS
    return rt


def _client() -> CmsClient:
    if _cms_client is None:
        raise RuntimeError("CMS client not initialized – call run_server() first")
    return _cms_client


def _ctx() -> tuple[str, str]:
    """Return (user_id, client_name) from context vars."""
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)
    if not uid:
        raise ValueError("user_id not provided")
    if not client_name:
        raise ValueError("client_name not provided")
    return uid, client_name


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool(
    description="Add a new memory. Called when the user shares personal info, "
    "preferences, or asks you to remember something.",
)
async def add_memories(text: str) -> str:
    try:
        uid, client_name = _ctx()
    except ValueError as e:
        return f"Error: {e}"

    try:
        request = cms_models.AddMemoriesRequest(
            messages=[cms_models.AddMemoriesRequestMessages(content=text, role="user")],
            user_id=uid,
            agent_id=client_name,
            infer=True,
            metadata={"mcp_client": client_name},
        )
        response = await asyncio.to_thread(
            _client().add_memories_with_options,
            _workspace,
            _memory_store,
            request,
            {},
            _runtime(),
        )
        body = response.body
        results = []
        if body and body.results:
            for r in body.results:
                results.append({
                    "event_id": r.event_id,
                    "message": r.message,
                    "status": r.status,
                })
        return json.dumps(
            {"request_id": body.request_id if body else None, "results": results},
            ensure_ascii=False,
        )
    except Exception as e:
        logger.exception("Error adding memory")
        return f"Error adding memory: {e}"


@mcp.tool(
    description="Search through stored memories. Called whenever the user asks anything.",
)
async def search_memory(query: str) -> str:
    try:
        uid, client_name = _ctx()
    except ValueError as e:
        return f"Error: {e}"

    try:
        request = cms_models.SearchMemoriesRequest(
            query=query,
            user_id=uid,
            agent_id=client_name,
            top_k=10,
        )
        response = await asyncio.to_thread(
            _client().search_memories_with_options,
            _workspace,
            _memory_store,
            request,
            {},
            _runtime(),
        )
        body = response.body
        results = []
        if body and body.results:
            for r in body.results:
                results.append({
                    "id": r.id,
                    "memory": r.memory,
                    "score": r.score,
                    "user_id": r.user_id,
                    "agent_id": r.agent_id,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                    "hash": r.hash,
                    "metadata": r.metadata,
                })
        relations = []
        if body and body.relations:
            for rel in body.relations:
                relations.append({
                    "source": rel.source,
                    "relationship": rel.relationship,
                    "destination": rel.destination,
                })
        return json.dumps(
            {"results": results, "relations": relations},
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        logger.exception("Error searching memory")
        return f"Error searching memory: {e}"


@mcp.tool(description="List all memories for the current user.")
async def list_memories() -> str:
    try:
        uid, client_name = _ctx()
    except ValueError as e:
        return f"Error: {e}"

    try:
        request = cms_models.GetMemoriesRequest(
            user_id=uid,
            agent_id=client_name,
        )
        response = await asyncio.to_thread(
            _client().get_memories_with_options,
            _workspace,
            _memory_store,
            request,
            {},
            _runtime(),
        )
        body = response.body
        results = []
        if body and body.results:
            for r in body.results:
                results.append({
                    "id": r.id,
                    "memory": r.memory,
                    "score": r.score,
                    "user_id": r.user_id,
                    "agent_id": r.agent_id,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                    "hash": r.hash,
                    "metadata": r.metadata,
                })
        return json.dumps({"results": results}, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.exception("Error listing memories")
        return f"Error listing memories: {e}"


@mcp.tool(description="Delete specific memories by their IDs.")
async def delete_memories(memory_ids: list[str]) -> str:
    try:
        _ctx()
    except ValueError as e:
        return f"Error: {e}"

    deleted = 0
    errors = []
    for mid in memory_ids:
        try:
            await asyncio.to_thread(
                _client().delete_memory_with_options,
                _workspace,
                _memory_store,
                mid,
                {},
                _runtime(),
            )
            deleted += 1
        except Exception as e:
            errors.append(f"{mid}: {e}")

    result = f"Successfully deleted {deleted}/{len(memory_ids)} memories"
    if errors:
        result += f". Errors: {'; '.join(errors)}"
    return result


@mcp.tool(description="Delete all memories for the current user.")
async def delete_all_memories() -> str:
    try:
        uid, client_name = _ctx()
    except ValueError as e:
        return f"Error: {e}"

    try:
        request = cms_models.DeleteMemoriesRequest(
            user_id=uid,
            agent_id=client_name,
        )
        await asyncio.to_thread(
            _client().delete_memories_with_options,
            _workspace,
            _memory_store,
            request,
            {},
            _runtime(),
        )
        return "Successfully deleted all memories"
    except Exception as e:
        logger.exception("Error deleting all memories")
        return f"Error deleting all memories: {e}"


# ---------------------------------------------------------------------------
# SSE Transport & FastAPI
# ---------------------------------------------------------------------------

mcp_router = APIRouter(prefix="/mcp")
sse = SseServerTransport("/mcp/messages/")


@mcp_router.get("/{client_name}/sse/{user_id}")
async def handle_sse(request: Request):
    uid = request.path_params.get("user_id")
    client_name = request.path_params.get("client_name")

    user_token = user_id_var.set(uid or "")
    client_token = client_name_var.set(client_name or "")

    try:
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,
        ) as (read_stream, write_stream):
            await mcp._mcp_server.run(
                read_stream,
                write_stream,
                mcp._mcp_server.create_initialization_options(),
            )
    finally:
        user_id_var.reset(user_token)
        client_name_var.reset(client_token)


@mcp_router.post("/messages/")
async def handle_messages(request: Request):
    try:
        body = await request.body()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            return {}

        await sse.handle_post_message(request.scope, receive, send)
        return {"status": "ok"}
    except Exception as e:
        logger.exception("Error handling message")
        return {"status": "error", "detail": str(e)}


def _create_app() -> FastAPI:
    app = FastAPI(
        title="AgentLoop Memory MCP Server",
        description="MCP Server for Alibaba Cloud Memory service (CMS 20240330)",
    )
    mcp._mcp_server.name = "agentloop-memory-mcp-server"
    app.include_router(mcp_router)
    return app


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_server(
    *,
    region_id: str,
    workspace: str,
    memory_store: str,
    access_key_id: Optional[str] = None,
    access_key_secret: Optional[str] = None,
    host: str = "0.0.0.0",
    port: int = 8080,
    log_level: str = "INFO",
) -> None:
    """Initialize CMS client, build FastAPI app, and start uvicorn."""
    import uvicorn

    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO))

    global _cms_client, _workspace, _memory_store

    config = _create_cms_config(access_key_id, access_key_secret)
    config.endpoint = cms_endpoint(region_id)
    _cms_client = CmsClient(config)
    _workspace = workspace
    _memory_store = memory_store

    logger.info(
        "Starting AgentLoop Memory MCP Server "
        f"(region={region_id}, workspace={workspace}, memory_store={memory_store})"
    )

    app = _create_app()
    uvicorn.run(app, host=host, port=port)
