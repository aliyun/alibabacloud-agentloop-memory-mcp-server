# alibabacloud-agentloop-memory-mcp-server

基于阿里云 CMS (alibabacloud_cms20240330) SDK 的 Memory MCP Server，提供记忆管理能力，支持通过 MCP 协议（SSE 传输）进行记忆的增删改查和语义搜索。

## 安装

```bash
pip install alibabacloud-agentloop-memory-mcp-server
```

## 快速开始

### 1. 配置环境变量

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID=your_access_key_id
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=your_access_key_secret
export ALIBABA_CLOUD_WORKSPACE=your_workspace_name
export ALIBABA_CLOUD_MEMORY_STORE=your_memory_store_name
```

### 2. 启动服务

```bash
# 使用 python -m 启动
python -m mcp_server_agentloop_memory

# 或使用命令行入口
alibabacloud-agentloop-memory-mcp-server

# 指定参数启动
python -m mcp_server_agentloop_memory \
  --access-key-id <your_ak_id> \
  --access-key-secret <your_ak_secret> \
  --workspace <workspace_name> \
  --memory-store <memory_store_name> \
  --region-id cn-hangzhou \
  --port 8765
```

### 3. 连接 MCP Client

服务启动后，MCP Client 通过 SSE 连接：

```
GET http://localhost:8765/mcp/{client_name}/sse/{user_id}
```

- `client_name`：客户端标识（如 `cursor`、`my-agent`），映射为 `agent_id`
- `user_id`：用户标识，用于隔离不同用户的记忆数据

## CLI 参数

| 参数 | 环境变量 | 默认值 | 说明 |
|------|---------|--------|------|
| `--access-key-id` | `ALIBABA_CLOUD_ACCESS_KEY_ID` | - | 阿里云 AccessKey ID |
| `--access-key-secret` | `ALIBABA_CLOUD_ACCESS_KEY_SECRET` | - | 阿里云 AccessKey Secret |
| `--region-id` | `ALIBABA_CLOUD_REGION_ID` | `cn-hangzhou` | 阿里云区域 |
| `--workspace` | `ALIBABA_CLOUD_WORKSPACE` | - | CMS Workspace 名称 |
| `--memory-store` | `ALIBABA_CLOUD_MEMORY_STORE` | - | Memory Store 名称 |
| `--host` | - | `0.0.0.0` | 监听地址 |
| `--port` | - | `8765` | 监听端口 |
| `--log-level` | - | `INFO` | 日志级别 |

## MCP Tools

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `add_memories` | `text: str` | 添加记忆。当用户分享个人信息、偏好或要求记住某些内容时调用 |
| `search_memory` | `query: str` | 语义搜索记忆。用户提问时调用 |
| `list_memories` | 无 | 列出当前用户的所有记忆 |
| `delete_memories` | `memory_ids: list[str]` | 按 ID 删除指定记忆 |
| `delete_all_memories` | 无 | 删除当前用户的所有记忆 |

## 权限要求

需要阿里云 RAM 用户具有 CMS Memory 相关 API 的访问权限。获取和管理 AccessKey 请参考 [阿里云 AccessKey 管理](https://help.aliyun.com/document_detail/53045.html)。

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试（需要配置环境变量）
pytest tests/ -v
```

## License

Apache-2.0
