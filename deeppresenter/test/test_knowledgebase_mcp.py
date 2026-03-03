#!/usr/bin/env python3
"""
知识库 MCP 服务测试脚本
测试 knowledgebase MCP 服务的连接和工具调用
工具: sessions_search, files_list
"""

import asyncio
import json
import sys
from pathlib import Path
from contextlib import AsyncExitStack

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 直接使用 MCP SDK
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


def print_section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def print_success(msg: str):
    print(f"✅ {msg}")


def print_error(msg: str):
    print(f"❌ {msg}")


def print_warning(msg: str):
    print(f"⚠️  {msg}")


def print_info(msg: str):
    print(f"ℹ️  {msg}")


async def test_mcp_connection(url: str, timeout: int = 10):
    """测试 MCP 连接和工具调用"""

    print_info(f"连接 URL: {url}")

    exit_stack = AsyncExitStack()
    session = None
    tools = []

    try:
        # 1. 创建连接
        print_info("创建 streamable-http 传输...")
        streamable_http_transport = await exit_stack.enter_async_context(
            streamablehttp_client(url)
        )

        # streamablehttp_client 可能返回 2 或 3 个值，取决于版本
        if len(streamable_http_transport) == 2:
            read_stream, write_stream = streamable_http_transport
        else:
            read_stream, write_stream, _ = streamable_http_transport

        print_info("创建客户端会话...")
        session = await exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        print_info("初始化会话...")
        await asyncio.wait_for(session.initialize(), timeout=timeout)
        print_success("MCP 会话连接成功！")

        # 2. 列出工具
        print_section("可用工具")

        tools_response = await session.list_tools()
        tools = tools_response.tools

        print_success(f"发现 {len(tools)} 个工具:")
        for tool in tools:
            print(f"\n  📦 {tool.name}")
            if hasattr(tool, 'description') and tool.description:
                print(f"     描述: {tool.description}")

        # 3. 测试 files_list 工具（不需要参数）
        print_section("测试 files_list")

        files_list_tool = next((t for t in tools if t.name == "files_list"), None)
        if files_list_tool:
            try:
                print_info("调用 files_list (无参数)...")
                result = await session.call_tool("files_list", {
                    "knowledge_bases": ["2025101716_905bcb877a2d63af34ccc4cfab006f2899526_lv0"],
                    "page": 1,
                    "page_size": 5
                })

                print_success("files_list 调用成功")

                # 解析结果
                if hasattr(result, 'content'):
                    for content_item in result.content:
                        if hasattr(content_item, 'text'):
                            text = content_item.text
                            try:
                                json_result = json.loads(text)
                                total = json_result.get('total', 0) if isinstance(json_result, dict) else 0
                                files = json_result.get('files', json_result) if isinstance(json_result, dict) else json_result
                                print(f"\n  文件总数: {total}")
                                if isinstance(files, list) and len(files) > 0:
                                    print(f"  文件列表 (前 {len(files)} 个):")
                                    for f in files[:3]:
                                        print(f"    - {f.get('file_name', f.get('name', '未知'))}")
                                else:
                                    print(f"  结果: {json.dumps(json_result, indent=4, ensure_ascii=False)[:300]}")
                            except json.JSONDecodeError:
                                print(f"  原始响应: {text[:200]}")

            except Exception as e:
                print_error(f"files_list 调用失败: {e}")
                import traceback
                traceback.print_exc()
        else:
            print_warning("files_list 工具不存在")

        # 4. 测试 sessions_search 工具
        print_section("测试 sessions_search")

        sessions_search_tool = next((t for t in tools if t.name == "sessions_search"), None)
        if sessions_search_tool:
            try:
                print_info("调用 sessions_search...")
                result = await session.call_tool("sessions_search", {
                    "question": "什么是LangChain",
                    "top_n": 3,
                    "knowledge_bases": ["2025101716_905bcb877a2d63af34ccc4cfab006f2899526_lv0"],
                    "score_threshold": 0.65
                })

                print_success("sessions_search 调用成功")

                # 解析结果
                if hasattr(result, 'content'):
                    for content_item in result.content:
                        if hasattr(content_item, 'text'):
                            text = content_item.text
                            try:
                                json_result = json.loads(text)
                                total = json_result.get('total', 0) if isinstance(json_result, dict) else 0
                                sessions = json_result.get('sessions', json_result) if isinstance(json_result, dict) else json_result
                                print(f"\n  匹配数量: {total}")
                                if isinstance(sessions, list) and len(sessions) > 0:
                                    print(f"  检索结果 (前 {len(sessions)} 条):")
                                    for s in sessions[:2]:
                                        content = s.get('content', '')[:100]
                                        print(f"    - {content}...")
                                else:
                                    print(f"  结果: {json.dumps(json_result, indent=4, ensure_ascii=False)[:300]}")
                            except json.JSONDecodeError:
                                print(f"  原始响应: {text[:200]}")

            except Exception as e:
                print_error(f"sessions_search 调用失败: {e}")
                import traceback
                traceback.print_exc()
        else:
            print_warning("sessions_search 工具不存在")

        # 清理
        await exit_stack.aclose()
        return True

    except asyncio.TimeoutError:
        print_error(f"连接超时 (超过 {timeout} 秒)")
        await exit_stack.aclose()
        return False

    except Exception as e:
        print_error(f"发生错误: {e}")
        import traceback
        traceback.print_exc()
        await exit_stack.aclose()
        return False


async def main():
    """主函数，测试多个 URL"""

    # 要测试的 URL 列表
    test_urls = [
        ("http://localhost:8088", "localhost:8088"),
        ("http://localhost:8088/", "localhost:8088/"),
        ("http://localhost:8088/mcp", "localhost:8088/mcp"),
        ("http://192.168.51.7:8088", "192.168.51.7:8088"),
    ]

    print("=" * 60)
    print("  知识库 MCP 服务测试")
    print("  工具: sessions_search, files_list")
    print("=" * 60)
    print(f"\n将依次测试 {len(test_urls)} 个 URL 配置...\n")

    for url, description in test_urls:
        print(f"\n{'=' * 60}")
        print(f"  测试: {description}")
        print('=' * 60)

        success = await test_mcp_connection(url=url, timeout=5)

        if success:
            print(f"\n🎉 {description} 连接成功！")
            print(f"\n💡 建议使用: {url}")
            return 0
        else:
            print(f"\n❌ {description} 连接失败")

    print("\n" + "=" * 60)
    print("  测试总结")
    print("=" * 60)
    print("\n❌ 所有 URL 配置均测试失败")
    print("\n请检查:")
    print("  1. 知识库 MCP 服务是否已启动: make kb_mcp_http")
    print("  2. 服务监听的端口是否为 8088")
    print("  3. 网络连接是否正常 (host 网络模式)")
    return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
