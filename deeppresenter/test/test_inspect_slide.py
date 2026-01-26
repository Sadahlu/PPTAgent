"""
独立测试 inspect_slide 功能（不依赖 MCP 装饰器）
"""
import asyncio
import base64
import tempfile
from pathlib import Path

from openai import AsyncOpenAI
from pptagent.utils import ppt_to_images
from deeppresenter.utils.webview import convert_html_to_pptx

from deeppresenter.utils.config import GLOBAL_CONFIG


async def test_inspect_slide_function(html_file: str, aspect_ratio: str = "widescreen"):
    """
    直接测试 inspect_slide 的核心功能
    """
    ASPECT_RATIO_MAPPING = {
        "16:9": "widescreen",
        "4:3": "normal",
    }

    if aspect_ratio in ASPECT_RATIO_MAPPING:
        aspect_ratio = ASPECT_RATIO_MAPPING[aspect_ratio]

    html_path = Path(html_file).absolute()

    # 验证输入
    if not html_path.exists():
        return f"❌ HTML 文件不存在: {html_path}"
    if html_path.suffix != ".html":
        return f"❌ 不是 HTML 文件: {html_path}"
    if aspect_ratio not in ["widescreen", "normal", "A1"]:
        return f"❌ aspect_ratio 必须是 'widescreen', 'normal', 'A1' 之一"

    try:
        print(f"✓ 正在转换 HTML 到 PPTX...")
        pptx_path = convert_html_to_pptx(html_path, aspect_ratio=aspect_ratio)
        print(f"  生成的 PPTX: {pptx_path}")

        print(f"✓ 正在将 PPTX 转换为图像...")
        # 创建持久化的输出目录
        output_dir = Path("test_images_output")
        output_dir.mkdir(exist_ok=True)

        print(f"输出目录: {output_dir.absolute()}")
        ppt_to_images(str(pptx_path), str(output_dir))
        image_path = output_dir / "slide_0001.jpg"

        if not image_path.exists():
            return f"❌ 图像生成失败，未找到 {image_path}"
        else:
            print(f"图像已保存到: {image_path.absolute()}")

        image_data = image_path.read_bytes()
        print(f"  生成的图像大小: {len(image_data)} bytes")

        base64_data = f"data:image/jpeg;base64,{base64.b64encode(image_data).decode('utf-8')}"

        return {
            "status": "success",
            "message": "✅ inspect_slide 功能正常",
            "image_size": len(image_data),
            "image_path": str(image_path.absolute()),
            "base64_preview": base64_data[:100] + "...",  # 只显示前100个字符
        }
    except Exception as e:
        return f"❌ 错误: {type(e).__name__}: {str(e)}"


async def send_image_to_design_agent(base64_data: str, prompt: str = "请描述这张幻灯片的内容、设计和布局。"):
    """
    将 base64 图像数据发送给 Design Agent 模型进行分析

    Args:
        base64_data: 完整的 base64 数据字符串，格式为 "data:image/jpeg;base64,..."
        prompt: 发送给模型的提示词

    Returns:
        模型的响应内容
    """
    # 配置（从 config.yaml 中读取）
    config = GLOBAL_CONFIG
    design_llm = config.design_agent
    model = design_llm.model
    base_url = design_llm.base_url
    api_key = design_llm.api_key

    try:
        # 创建 OpenAI 客户端
        client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
        )

        print(f"✓ 正在调用 Design Agent 模型...")
        print(f"  模型: {model}")
        print(f"  提示词: {prompt}")

        # 发送请求
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": base64_data
                            }
                        }
                    ]
                }
            ],
            max_tokens=2048,
        )
        # 提取响应内容
        content = response.choices[0].message.content
        print(f"✓ 模型响应成功")
        print(f"  使用 tokens: {response.usage.total_tokens if response.usage else 'N/A'}")

        return {
            "status": "success",
            "content": content,
            "model": model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            } if response.usage else None
        }

    except Exception as e:
        return {
            "status": "error",
            "error": f"{type(e).__name__}: {str(e)}"
        }



async def main():
    # 测试用例
    html_file = "/root/.cache/deeppresenter/20260116/41d1ec81/slides/slide_01.html"

    print(f"{'='*60}")
    print(f"测试 inspect_slide 功能")
    print(f"{'='*60}")
    print(f"HTML 文件: {html_file}")
    print(f"纵横比: widescreen")
    print()

    # 第一步：生成图像
    result = await test_inspect_slide_function(html_file, aspect_ratio="widescreen")

    if isinstance(result, dict) and result.get("status") == "success":
        print(f"\n第一步结果:")
        for key, value in result.items():
            if key != "base64_preview":  # 跳过显示 base64 预览
                print(f"  {key}: {value}")

        # 第二步：将图像发送给 Design Agent
        print(f"\n{'='*60}")
        print(f"测试 Design Agent 模型分析")
        print(f"{'='*60}\n")

        # 重新读取完整的 base64 数据
        image_path = Path(result["image_path"])
        image_data = image_path.read_bytes()
        base64_data = f"data:image/jpeg;base64,{base64.b64encode(image_data).decode('utf-8')}"

        # 调用 Design Agent
        agent_result = await send_image_to_design_agent(
            base64_data=base64_data,
            prompt="请详细描述这张幻灯片的内容、设计元素和布局结构。"
        )

        print(f"\n第二步结果:")
        if agent_result["status"] == "success":
            print(f"  模型: {agent_result['model']}")
            print(f"  响应内容:")
            print(f"    {agent_result['content']}")
            if agent_result['usage']:
                print(f"  Token 使用:")
                print(f"    Prompt: {agent_result['usage']['prompt_tokens']}")
                print(f"    Completion: {agent_result['usage']['completion_tokens']}")
                print(f"    Total: {agent_result['usage']['total_tokens']}")
        else:
            print(f"  错误: {agent_result['error']}")
    else:
        print(f"\n结果: {result}")


if __name__ == "__main__":
    asyncio.run(main())
