# Design Agent 的 response_format 决定机制分析

## 核心发现：Design Agent 从不使用 response_format！

### Agent 的两个方法

```python
# agent.py:130-158
async def chat(self, message, response_format=None):
    """普通对话，可以要求结构化输出"""
    response = await self.llm.run(
        messages=self.chat_history,
        response_format=response_format,  # ← 可以传入
    )

# agent.py:160-207
async def action(self):
    """工具调用，不使用结构化输出"""
    response = await self.llm.run(
        messages=self.chat_history,
        tools=self.tools,  # ← 只传递 tools
    )
```

---

## Design Agent 的实际调用

```python
# design.py:6-19
class Design(Agent):
    async def loop(self, req: InputRequest, markdown_file: str):
        while True:
            agent_message = await self.action(  # ← 只用 action()！
                markdown_file=markdown_file,
                prompt=req.webagent_prompt
            )
            yield agent_message
            outcome = await self.execute(agent_message.tool_calls)
            if not isinstance(outcome, list):
                break
        yield outcome
```

**关键点**：Design Agent 只调用 `action()`，从不调用 `chat()`

---

## LLM.run() 的三种模式

```python
# config.py:166-186
async def _call(self, client, model, messages, sampling_params,
                response_format=None, tools=None, retry_times=3):

    for retry_idx in range(retry_times):
        try:
            # 模式 1: 工具调用（Design Agent 走这里）
            if tools is not None:
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tools,  # ← 有 tools
                    tool_choice="auto",
                    **sampling_params,
                )

            # 模式 2: 结构化输出（Design Agent 不走这里）
            elif not self.soft_response_parsing and response_format is not None:
                response = await client.chat.completions.parse(
                    model=model,
                    messages=messages,
                    response_format=response_format,  # ← 需要 response_format
                    **sampling_params,
                )

            # 模式 3: 普通对话（Design Agent 也不走这里）
            else:
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    **sampling_params,
                )
```

---

## 决策流程图

```
用户请求
    ↓
Design.loop()
    ↓
await self.action() ← 固定调用，不传 response_format
    ↓
llm.run(messages=..., tools=self.tools) ← 只传 tools
    ↓
_call(tools=self.tools, response_format=None) ← response_format=None
    ↓
if tools is not None:  ← 条件成立！
    ↓
client.chat.completions.create(tools=tools) ← 工具调用模式
    ↓
模型返回 tool_calls (不是结构化 JSON)
```

**结论**：`response_format` 在 Design Agent 中**永远是 None**，不参与决策。

---

## 为什么 Design Agent 不需要 response_format？

### 工作流程：

1. **调用工具阶段**：
   ```
   用户: "创建幻灯片"
   ↓
   Design Agent → LLM: "你有这些工具: [write_file, inspect_slide, thinking, finalize]"
   ↓
   LLM 返回: tool_calls = [{"name": "write_file", "arguments": {"path": "...", "content": "<html>..."}}]
   ↓
   Agent 执行工具 → 写入 HTML 文件
   ```

2. **生成 HTML 内容**：
   - HTML 内容在 `tool_calls[0].arguments.content` 中
   - 这是**字符串参数**，不需要结构化验证
   - LLM 自由生成 HTML，工具调用的 JSON 结构由 OpenAI API 保证

---

## 对比：什么时候需要 response_format？

假设有一个 "Planner Agent" 需要返回计划：

```python
class Planner(Agent):
    async def create_plan(self, task: str):
        # 使用 chat() 方法，传入 response_format
        response = await self.chat(
            message=ChatMessage(role="user", content=f"为任务制定计划: {task}"),
            response_format=PlanSchema  # ← 需要结构化输出
        )
        # 返回的是验证过的 Pydantic 对象
        return response.content

class PlanSchema(BaseModel):
    steps: list[str]
    estimated_time: int
    resources: list[str]
```

这种场景下：
- 不是工具调用
- 需要保证返回的 JSON 符合特定格式
- 使用 `response_format` 约束输出

---

## 实际测试验证

让我们验证 Design Agent 是否真的不用 response_format：

```python
# 在 design.py 中添加日志
async def loop(self, req: InputRequest, markdown_file: str):
    while True:
        print(f"DEBUG: Calling action() with tools={len(self.tools)} tools")
        agent_message = await self.action(...)
        print(f"DEBUG: Got tool_calls={agent_message.tool_calls}")
        # ...
```

预期输出：
```
DEBUG: Calling action() with tools=4 tools
DEBUG: Got tool_calls=[ChatCompletionMessageToolCall(id='...', function=Function(name='write_file', ...))]
```

**永远不会看到 response_format 参数！**

---

## 为什么 Qwen 仍然报错？

如果 Design Agent 不用 response_format，为什么还会报错 `NoneType: None`？

可能的原因：

1. **Research Agent 用了**：
   ```python
   # 如果 Research Agent 使用了 chat() + response_format
   # 那么错误来自 Research Agent，不是 Design Agent
   ```

2. **工具调用本身失败**：
   ```python
   # config.py:195-196
   assert tools is None or message.tool_calls, "No tool call returned"
   # 如果 Qwen 不支持 function calling，这里会失败
   ```

3. **message.content 为空**：
   ```python
   # config.py:198-199
   assert message.tool_calls or message.content, "Empty content"
   # 如果既没有 tool_calls 也没有 content，会报错
   ```

---

## 总结

| 问题 | 答案 |
|------|------|
| **response_format 谁输入？** | 调用者在 `chat()` 方法中传入 |
| **Design Agent 是否使用？** | ❌ 不使用，只用 `action()` |
| **如何决定用不用？** | 不是智能决定，是代码逻辑固定的 |
| **工具调用 vs 结构化输出** | 互斥！有 tools 就不用 response_format |
| **Design Agent 的模式** | 纯工具调用，HTML 在工具参数中 |

**核心逻辑**：
```python
if tools:        # Design Agent 走这里
    使用工具调用模式
elif response_format:  # Design Agent 不走这里
    使用结构化输出模式
else:            # Design Agent 也不走这里
    普通对话模式
```

Design Agent 的 `soft_response_parsing` 报错**不是因为 response_format**，而是因为：
- 可能工具调用本身失败
- 或者模型返回了空响应

需要运行 `test_design_agent.py` 来确诊真正原因！
