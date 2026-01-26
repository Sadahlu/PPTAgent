#!/usr/bin/env python3
"""分析 PPTAgent history，查看 LLM 调用 create_slide 前是否有 available_layouts 上下文"""

import jsonlines
import json
import sys

history_file = '/root/.cache/deeppresenter/20260107/cb675423/history/PPTAgent-history.jsonl'

# 读取所有消息
with jsonlines.open(history_file) as reader:
    messages = [msg for msg in reader if msg is not None]  # 过滤 None

print(f"总共 {len(messages)} 条消息\n")

# 找到 set_template 的返回
set_template_idx = None
for i, msg in enumerate(messages):
    if not isinstance(msg, dict):  # 跳过非字典类型
        continue
    if msg.get('from_tool', {}).get('name') == 'set_template':
        set_template_idx = i
        print(f"{'='*70}")
        print(f"Message {i}: set_template 工具返回")
        print(f"{'='*70}")
        content = json.loads(msg['content'][0]['text'])
        print(f"\nAvailable layouts ({len(content['available_layouts'])} 个):")
        for layout in content['available_layouts']:
            print(f"  ✓ {layout}")
        print()
        break

if set_template_idx is None:
    print("错误：没有找到 set_template 调用")
    sys.exit(1)

# 显示下一条消息（LLM 的响应）
print(f"{'='*70}")
print(f"Message {set_template_idx + 1}: LLM 立即响应")
print(f"{'='*70}")
if set_template_idx + 1 >= len(messages):
    print("错误：set_template 后没有更多消息")
    sys.exit(1)

next_msg = messages[set_template_idx + 1]
if not isinstance(next_msg, dict):
    print(f"错误：下一条消息不是字典类型: {type(next_msg)}")
    sys.exit(1)

if next_msg.get('tool_calls'):
    for tc in next_msg['tool_calls']:
        args_dict = json.loads(tc['function']['arguments'])
        print(f"Tool call: {tc['function']['name']}")
        print(f"Arguments: {json.dumps(args_dict, indent=2, ensure_ascii=False)}")
        if tc['function']['name'] == 'create_slide':
            layout_used = args_dict.get('layout', 'N/A')
            # 检查是否在 available_layouts 中
            available = content['available_layouts']
            if layout_used in available:
                print(f"  ✓ Layout '{layout_used}' 在 available_layouts 中")
            else:
                print(f"  ✗ Layout '{layout_used}' 不在 available_layouts 中！")
                print(f"  最相似的候选：")
                for avail in available[:3]:
                    print(f"    - {avail}")
else:
    print("没有工具调用")
print()

# 统计所有 create_slide 调用的 layout 使用情况
print(f"{'='*70}")
print("set_template 之后的所有 create_slide 调用")
print(f"{'='*70}")
available_layouts = content['available_layouts']
layout_stats = {}
errors = []

for i in range(set_template_idx + 1, len(messages)):
    msg = messages[i]
    if not isinstance(msg, dict):  # 跳过非字典类型
        continue
    if msg.get('tool_calls'):
        for tc in msg['tool_calls']:
            if tc['function']['name'] == 'create_slide':
                args = json.loads(tc['function']['arguments'])
                layout = args.get('layout', 'N/A')
                layout_stats[layout] = layout_stats.get(layout, 0) + 1

                if layout not in available_layouts:
                    errors.append((i, layout))

print(f"\n使用的 layout 统计：")
for layout, count in sorted(layout_stats.items(), key=lambda x: -x[1]):
    status = "✓" if layout in available_layouts else "✗"
    print(f"  {status} '{layout}': {count} 次")

print(f"\n错误统计：")
print(f"  总调用: {sum(layout_stats.values())} 次")
print(f"  正确: {sum(1 for l in layout_stats.keys() if l in available_layouts)} 种 layout")
print(f"  错误: {len(errors)} 次调用使用了不存在的 layout")
if sum(layout_stats.values()) > 0:
    print(f"  错误率: {len(errors) / sum(layout_stats.values()) * 100:.1f}%")

if errors:
    print(f"\n前 3 个错误示例：")
    for i, layout in errors[:3]:
        print(f"  Message {i}: '{layout}'")

# 检查 chat_history 完整性
print(f"\n{'='*70}")
print("检查 chat_history 完整性")
print(f"{'='*70}")
print(f"set_template 索引: {set_template_idx}")

# 检查是否有其他消息干扰
print(f"\n从 set_template({set_template_idx}) 开始的消息：")
for i in range(set_template_idx, min(set_template_idx + 5, len(messages))):
    msg = messages[i]
    if not isinstance(msg, dict):
        print(f"  [{i}] 非字典类型: {type(msg)}")
        continue
    role = msg.get('role', 'unknown')
    if msg.get('from_tool'):
        tool_name = msg['from_tool']['name']
        content_preview = str(msg.get('content', ''))[:100]
        print(f"  [{i}] role={role}, from_tool={tool_name}")
        print(f"       content preview: {content_preview}...")
    elif msg.get('tool_calls'):
        tools = [tc['function']['name'] for tc in msg['tool_calls']]
        print(f"  [{i}] role={role}, tool_calls={tools}")
    else:
        content_len = len(str(msg.get('content', '')))
        print(f"  [{i}] role={role}, content_len={content_len}")

print(f"\n结论：")
print(f"  1. set_template 返回了 {len(available_layouts)} 个可用 layout")
print(f"  2. LLM 使用了 {len(layout_stats)} 种 layout 名称")
print(f"  3. 其中 {len([l for l in layout_stats.keys() if l not in available_layouts])} 种不在 available_layouts 中")
if len(errors) > 0:
    print(f"  4. 这证明 LLM **忽略了** set_template 的返回值！")
else:
    print(f"  4. 所有 layout 都正确！")
