#!/usr/bin/env python3
"""
Design Agent 失败诊断工具
诊断 config.py:207 错误的所有可能原因
"""

import asyncio
import json
import sys
import traceback
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from openai import AsyncOpenAI
from pydantic import BaseModel

from deeppresenter.utils.config import GLOBAL_CONFIG, get_json_from_response


class TestSchema(BaseModel):
    """测试用的简单 Schema"""

    title: str
    content: str


def print_section(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


async def test_design_agent_failure():
    """逐一排查导致 Design Agent 失败的原因"""
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "获取天气信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "城市名称"}
                    },
                    "required": ["location"],
                },
            },
        }
    ]

    print_section("Design Agent 失败诊断")

    # 1. 加载配置
    print_section("1. 加载配置")
    try:
        config = GLOBAL_CONFIG
        design_llm = config.design_agent
        design_model = design_llm.model
        base_url = design_llm.base_url
        api_key = design_llm.api_key

        print(f"✅ 配置加载成功")
        print(f"   Model: {design_model}")
        print(f"   Base URL: {base_url}")
        print(f"   soft_response_parsing: {design_llm.soft_response_parsing}")
        print(f"   use_qwen_tool_calling: {design_llm.use_qwen_tool_calling}")

    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        traceback.print_exc()
        return

    # 创建客户端
    client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=120)

    # 2. 测试可能的失败原因
    test_results = {}

    # 原因 1: response.choices 为空或 None
    print_section("2. 测试原因 1: response.choices 为空")
    try:
        response = await client.chat.completions.create(
            model=design_model,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10,
        )

        has_choices = response.choices is not None and len(response.choices) > 0
        test_results["has_choices"] = has_choices

        if has_choices:
            print(f"✅ response.choices 正常: {len(response.choices)} choices")
        else:
            print(f"❌ response.choices 为空或 None")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        test_results["has_choices"] = False

    # 原因 2: message.content 为 None
    print_section("3. 测试原因 2: message.content 为 None")
    try:
        response = await client.chat.completions.create(
            model=design_model,
            messages=[{"role": "user", "content": "你是谁"}],
            max_tokens=1000,
        )

        message = response.choices[0].message
        has_content = message.content is not None and len(message.content) > 0
        test_results["has_content"] = has_content

        if has_content:
            print(f"✅ message.content 正常: {message.content[:100]}")
        else:
            print(f"❌ message.content 为 None 或空字符串")
            print(f"   message.tool_calls: {message.tool_calls}")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        test_results["has_content"] = False

    # 原因 3: 使用 response_format (structured output)
    print_section("4. 测试原因 3: 结构化输出支持")

    # 3a. 测试 completions.parse() 方法
    print("\n测试 3a: client.chat.completions.parse()")
    try:
        response = await client.chat.completions.parse(
            model=design_model,
            messages=[
                {"role": "user", "content": "创建一个标题为'测试'，内容为'这是测试'的文档"}
            ],
            response_format=TestSchema,
            max_tokens=100,
        )

        message = response.choices[0].message
        has_parsed = message.parsed is not None
        test_results["supports_parse"] = has_parsed

        if has_parsed:
            print(f"✅ completions.parse() 成功")
            print(f"   解析结果: {message.parsed}")
        else:
            print(f"❌ completions.parse() 失败: message.parsed 为 None")
            print(f"   原始内容: {message.content}")

    except Exception as e:
        print(f"❌ completions.parse() 不支持: {e}")
        test_results["supports_parse"] = False

    # 3b. 测试手动 JSON 解析（soft_response_parsing）
    print("\n测试 3b: 手动 JSON 解析 (soft_response_parsing)")
    try:
        response = await client.chat.completions.create(
            model=design_model,
            messages=[
                {"role": "user", "content": "请返回 JSON 格式: {\"title\": \"测试\", \"content\": \"这是测试\"}"}
            ],
            response_format={"type": "json_object"},
            max_tokens=1000,
        )

        message = response.choices[0].message
        content = message.content

        if content:
            print(f"✅ 生成了 JSON 内容:")
            print(f"   原始内容: {content}")

            # 测试 get_json_from_response
            try:
                parsed = get_json_from_response(content)
                print(f"✅ get_json_from_response 解析成功: {parsed}")

                # 测试 Pydantic 验证
                try:
                    validated = TestSchema(**parsed)
                    print(f"✅ Pydantic 验证成功: {validated}")
                    test_results["soft_parsing_works"] = True
                except Exception as e:
                    print(f"❌ Pydantic 验证失败: {e}")
                    test_results["soft_parsing_works"] = False

            except Exception as e:
                print(f"❌ get_json_from_response 失败: {e}")
                test_results["soft_parsing_works"] = False
        else:
            print(f"❌ 返回内容为空")
            test_results["soft_parsing_works"] = False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        traceback.print_exc()
        test_results["soft_parsing_works"] = False

    # 原因 4: 工具调用
    print_section("5. 测试原因 4: 工具调用支持")
    try:
        use_design_agent = False
        if use_design_agent:
            response = await design_llm.run(
                messages=[{"role": "user", "content": "上海天气怎么样？"}],
                tools=tools,
                retry_times=1,
            )
        else:
            response = await client.chat.completions.create(
                model=design_model,
                messages=[{"role": "user", "content": "北京天气怎么样？"}],
                tools=tools
            )

        message = response.choices[0].message

        # 详细调试输出
        print("\n" + "=" * 60)
        print("DEBUG: 完整 message 对象信息")
        print("=" * 60)
        print(f"message.role: {message.role}")
        print(f"message.content: {repr(message.content)}")
        print(f"message.tool_calls: {message.tool_calls}")
        print(f"message.function_call: {getattr(message, 'function_call', None)}")
        print(f"message.refusal: {getattr(message, 'refusal', None)}")

        # 打印完整的 message 字典表示
        print("\nmessage 的完整 dict 表示:")
        try:
            message_dict = message.model_dump() if hasattr(message, 'model_dump') else message.dict()
            print(json.dumps(message_dict, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"无法序列化: {e}")
            print(f"message 对象: {message}")

        print("\nresponse.choices[0] 完整信息:")
        try:
            choice_dict = response.choices[0].model_dump() if hasattr(response.choices[0], 'model_dump') else response.choices[0].dict()
            print(json.dumps(choice_dict, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"无法序列化: {e}")
        print("=" * 60 + "\n")

        has_tool_calls = message.tool_calls is not None and len(message.tool_calls) > 0
        test_results["supports_tools"] = has_tool_calls

        if has_tool_calls:
            print(f"✅ 工具调用成功: {message.tool_calls}")
        else:
            print(f"⚠️  未返回工具调用（可能模型选择直接回答）")
            print(f"   返回内容: {message.content}")
            print(f"   内容长度: {len(message.content) if message.content else 0} 字符")

    except Exception as e:
        print(f"❌ 工具调用失败: {e}")
        test_results["supports_tools"] = False

    # 原因 5: 模拟 Design Agent 实际调用
    print_section("6. 模拟 Design Agent 实际调用")

    print("\n测试 6a: 使用 Design LLM 配置")
    try:
        # 使用实际的 Design LLM 对象（已在顶部定义）
        test_prompt = "杭州天气怎么样"

        response = await design_llm.run(
            messages=test_prompt,
            tools=tools,
            retry_times=1,
        )

        message = response.choices[0].message
        print(f"message:{message}")
        has_tool_calls = message.tool_calls is not None and len(message.tool_calls) > 0
        test_results["design_llm_works"] = has_tool_calls

        if has_tool_calls:
            print(f"✅ 工具调用成功: {message.tool_calls}")
        else:
            print(f"⚠️  未返回工具调用（可能模型选择直接回答）")
            print(f"   返回内容: {message.content}")
            print(f"   内容长度: {len(message.content) if message.content else 0} 字符")

    except Exception as e:
        print(f"❌ Design LLM 调用失败: {e}")
        traceback.print_exc()
        test_results["design_llm_works"] = False

    # 总结
    print_section("诊断总结")

    all_passed = all(test_results.values())

    print("\n测试结果:")
    for test_name, result in test_results.items():
        status = "✅" if result else "❌"
        print(f"  {status} {test_name}: {result}")

    if all_passed:
        print("\n✅ 所有测试通过，模型配置正常")
    else:
        print("\n❌ 发现问题，可能的解决方案:")

        if not test_results.get("has_choices"):
            print("\n  问题 1: response.choices 为空")
            print("  解决: 检查模型端点是否正确，API key 是否有效")

        if not test_results.get("has_content"):
            print("\n  问题 2: message.content 为 None")
            print("  解决: 检查模型配置，增加 max_tokens")

        if not test_results.get("supports_parse"):
            print("\n  问题 3: 不支持 completions.parse()")
            print("  解决: 在 config.yaml 中设置 soft_response_parsing: true")
            print("  位置: deeppresenter/deeppresenter/config.yaml")
            print("  添加:")
            print("    design_llm:")
            print("      soft_response_parsing: true")

        if not test_results.get("supports_tools"):
            print("\n  问题 4: 工具调用失败")
            print("  解决: 检查模型是否支持tools的使用")

        if not test_results.get("design_llm_works"):
            print("\n  问题 5: Design LLM 配置问题")
            print("  解决: 检查 config.yaml 中的 design_agent_model 配置")

    return test_results


if __name__ == "__main__":
    results = asyncio.run(test_design_agent_failure())

    # 返回状态码
    if results and all(results.values()):
        sys.exit(0)
    else:
        sys.exit(1)
