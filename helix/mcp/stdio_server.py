"""
Helix Runtime - MCP Stdio Server

通过 stdio 与 Claude Code 通信的 MCP 服务器
"""

import sys
import json
import asyncio
from typing import Optional, Dict, Any

from helix.mcp.handlers import MCPHandlers


async def run_stdio_server():
    """运行 stdio 服务器"""
    handlers = MCPHandlers()

    # 确保 stdin/stdout 是二进制模式以避免编码问题
    reader = asyncio.StreamReader()
    reader_protocol = asyncio.StreamReaderProtocol(reader)

    # 连接 stdin
    loop = asyncio.get_running_loop()
    await loop.connect_read_pipe(lambda: reader_protocol, sys.stdin)

    while True:
        try:
            # 读取一行请求
            line_bytes = await reader.readline()
            if not line_bytes:
                break

            line = line_bytes.decode('utf-8').strip()
            if not line:
                continue

            # 解析 JSON-RPC 请求
            request = json.loads(line)
            request_id = request.get('id')
            method = request.get('method')
            params = request.get('params')

            # 使用 MCPHandlers 处理请求
            result = await handlers.handle(method, params)

            # 构建响应
            if "error" in result:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": result["error"]
                }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result.get("result")
                }

            # 写入响应到 stdout
            response_json = json.dumps(response, ensure_ascii=False)
            sys.stdout.write(response_json + '\n')
            sys.stdout.flush()

        except json.JSONDecodeError:
            # JSON 解析错误
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": "PARSE_ERROR",
                    "message": "Invalid JSON",
                    "retryable": False
                }
            }
            sys.stdout.write(json.dumps(response) + '\n')
            sys.stdout.flush()
        except Exception:
            # 其他错误，继续运行
            pass


def main():
    """stdio 服务器入口点"""
    asyncio.run(run_stdio_server())


if __name__ == "__main__":
    main()
