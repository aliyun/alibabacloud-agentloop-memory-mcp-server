"""Runtime configuration constants for the Memory MCP Server."""

import os

READ_TIMEOUT_MS = int(os.getenv("READ_TIMEOUT_MS", "60000"))
CONNECT_TIMEOUT_MS = int(os.getenv("CONNECT_TIMEOUT_MS", "30000"))

CMS_ENDPOINT_TEMPLATE = "cms.{region}.aliyuncs.com"


def cms_endpoint(region_id: str) -> str:
    return CMS_ENDPOINT_TEMPLATE.format(region=region_id)
