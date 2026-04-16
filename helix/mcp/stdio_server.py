"""
Helix Runtime - MCP Stdio Server

最简单的实现 - 用于诊断连接问题
"""

import sys
import json


def run_stdio_server():
    """运行 stdio 服务器"""
    # 确保 stdout 无缓冲
    sys.stdout = open(sys.stdout.fileno(), 'w', buffering=1)

    while True:
        try:
            # 读取一行
            line = sys.stdin.readline()
            if not line:
                break

            line = line.strip()
            if not line:
                continue

            # 解析请求
            request = json.loads(line)
            request_id = request.get('id')
            method = request.get('method')

            # 最简单的响应
            if method == 'initialize':
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": True,
                            "resources": True,
                            "prompts": True
                        },
                        "serverInfo": {
                            "name": "helix-runtime",
                            "version": "0.2.0"
                        }
                    }
                }
            elif method == 'tools/list':
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": []
                    }
                }
            elif method == 'resources/list':
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "resources": []
                    }
                }
            elif method == 'prompts/list':
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "prompts": []
                    }
                }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": "METHOD_NOT_FOUND",
                        "message": f"Unknown method: {method}",
                        "retryable": False
                    }
                }

            # 写入响应
            json.dump(response, sys.stdout, ensure_ascii=False)
            sys.stdout.write('\n')
            sys.stdout.flush()

        except Exception:
            # 任何错误都继续
            pass
