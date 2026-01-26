"""
测试 Qwen 模型是否支持 OpenAI 格式的图像输入
"""
import asyncio
import base64
from pathlib import Path

from openai import AsyncOpenAI


async def test_qwen_image_input():
    """
    测试 Qwen 模型是否接受 OpenAI 格式的 base64 图像
    """
    # 配置（从你的 config.yaml 中读取）
    base_url = "http://192.168.50.9:18002/v1"
    model = "Qwen/Qwen3-Omni-30B-A3B-Instruct"
    api_key = "sk-cjcigurbfqpfuifbqnsubiafjwxmmnwlxrjmhjpmwbxrritq"

    client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    # 方法1：使用真实图像测试（如果有的话）
    test_image_path = Path("/app/PPTAgent/test_images_output/slide_0001.jpg")

    if test_image_path.exists():
        print("✓ 找到测试图像")
        image_data = test_image_path.read_bytes()
        base64_data = f"data:image/jpeg;base64,{base64.b64encode(image_data).decode('utf-8')}"
        print(f"  图像大小: {len(image_data)} bytes")
    else:
        # 方法2：使用 1x1 像素的红色 PNG 图像
        print("⚠️  测试图像不存在，使用最小示例图像")
        # 1x1 红色 PNG，base64 编码
        base64_data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="

    print(f"\n{'=' * 60}")
    print(f"测试 Qwen 模型图像支持")
    print(f"{'=' * 60}")
    print(f"模型: {model}")
    print(f"API: {base_url}")
    print()

    # 测试 1：用户消息中的图像（标准 OpenAI Vision API 格式）
    print("测试 1: USER role 中的图像 (标准格式)")
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "tool_call_id": "call_test123",
                    "content": [
                        {"type": "text", "text": "请描述这张图片的内容"},
                        {"type": "image_url", "image_url": {"url": base64_data}},
                    ],
                }
            ],
            max_tokens=100,
        )
        print(f"✅ 成功！响应: {response.choices[0].message.content[:200]}")
    except Exception as e:
        print(f"tool_call_id")
        print(f"❌ 失败: {type(e).__name__}: {str(e)}")

    # 测试 2：工具调用后的图像（TOOL role）
    print("\n测试 2: TOOL role 中的图像 (inspect_slide 使用的格式)")
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "请分析工具返回的图片"},
                {
                    "role": "tool",
                    "tool_call_id": "call_test123",
                    "content": [
                        {"type": "image_url", "image_url": {"url": base64_data}},
                    ],
                },
            ],
            max_tokens=100,
        )
        print(f"✅ 成功！响应: {response.choices[0].message.content[:200]}")
    except Exception as e:
        print(f"❌ 失败: {type(e).__name__}: {str(e)}")

    # 测试 3：检查模型是否声明支持 vision
    print("\n测试 3: 检查模型能力")
    try:
        models = await client.models.list()
        qwen_model = None
        for m in models.data:
            if "Qwen3-Omni" in m.id or model in m.id:
                qwen_model = m
                break

        if qwen_model:
            print(f"✅ 找到模型: {qwen_model.id}")
            # OpenAI 模型对象可能不包含详细能力信息
            print(f"   模型信息: {qwen_model}")
        else:
            print(f"⚠️  未找到模型，但这不一定意味着不支持")
    except Exception as e:
        print(f"⚠️  无法列出模型: {type(e).__name__}: {str(e)}")

    print(f"\n{'=' * 60}")
    print("总结:")
    print("- 如果测试 1 和测试 2 都成功，说明 Qwen 完全支持 inspect_slide 的图像格式")
    print("- 如果测试 1 成功但测试 2 失败，说明 Qwen 不支持 TOOL role 中的图像")
    print("- 如果都失败，检查:")
    print("  1. 模型是否真的支持视觉能力")
    print("  2. API 端点配置是否正确")
    print("  3. base64 图像格式是否正确")


if __name__ == "__main__":
    asyncio.run(test_qwen_image_input())
