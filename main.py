"""Hello Agent —— 最小可运行的 AI Agent（约 150 行）

它做的事，只有四步，然后循环：

    1. 把消息发给大模型
    2. 模型决定：直接回答，还是调用某个工具
    3. 如果要调工具，程序执行它，把结果塞回消息列表
    4. 回到第 1 步

这个循环，就是 LangGraph、AutoGen、Claude Code 全部框架的内核。
读懂这 150 行，你就理解了 80% 的 Agent。

运行：
    uv sync
    uv run python main.py "帮我算一下 23*47+8，再告诉我现在几点"
"""

import ast
import json
import operator
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

# Windows 控制台默认不是 UTF-8，避免中文乱码
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
if not API_KEY:
    raise SystemExit(
        "没有找到 DEEPSEEK_API_KEY。\n"
        "请在 hello-agent 目录下新建 .env 文件，写入：\n"
        "DEEPSEEK_API_KEY=sk-你的key"
    )

client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

MODEL = "deepseek-chat"
MAX_STEPS = 8          # 最多循环几轮，防止无限调用
NOTE_FILE = "notes.md"

SYSTEM_PROMPT = """你是一个只会说中文的助手。
规则：
1. 需要计算时调用 calculator，不要自己心算。
2. 需要知道当前时间时调用 get_current_time。
3. 用户让你记住某件事时调用 save_note。
4. 拿到工具结果后，用中文简洁地回答用户。
5.无论用户用什么语言提问，你都只能用中文回答。
"""

# ---------------------------------------------------------------------------
# 工具的定义：告诉模型"有哪些工具、怎么用"
# 这段 JSON Schema 决定了模型能不能正确调用，是 Agent 里最需要打磨的部分之一
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "计算数学表达式，支持 + - * / ** % 和括号，例如 (23*47)+8",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "要计算的表达式"}
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前日期和时间",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_note",
            "description": "把一条内容追加保存到 notes.md 文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "要保存的内容"}
                },
                "required": ["content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气，包括天气状况和气温。当用户询问某地天气、气温、是否下雨时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称，例如 合肥、北京、上海"}
                },
                "required": ["city"],
            },
        },
    },
    
]

# ---------------------------------------------------------------------------
# 工具的实现：模型只会"说要调什么"，真正干活的是下面这几个普通函数
# ---------------------------------------------------------------------------
_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def _eval_node(node):
    """只允许数字和四则运算，避免 eval 的安全问题。"""
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("只支持数字和 + - * / ** % 运算")


def calculator(expression: str) -> str:
    value = _eval_node(ast.parse(expression, mode="eval"))
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value)


def get_current_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def save_note(content: str) -> str:
    with open(NOTE_FILE, "a", encoding="utf-8") as f:
        f.write(f"- [{datetime.now():%Y-%m-%d %H:%M}] {content}\n")
    return f"已写入 {NOTE_FILE}"


def get_weather(city: str) -> str:
    fake = {"合肥": "晴,22°C", "北京": "多云,18°C","南京": "雨,99°C"}
    if city in fake:
        return fake[city]
    else:
        return f"{city}:暂无数据"
        
    # 要求：
    # 1. 建一个字典，存 3 个城市的假天气
    # 2. 用 .get() 查 city
    # 3. 查不到时返回一句默认的话
    # 4. 返回字符串
    

TOOL_FUNCS = {
    "calculator": calculator,
    "get_current_time": get_current_time,
    "save_note": save_note,
    "get_weather": get_weather,
}


def run_tool(name: str, arguments: str) -> str:
    """执行一次工具调用。注意：任何异常都变成字符串返回给模型，而不是让程序崩溃。

    这就是 Agent 能"自我修复"的秘密：模型看到错误信息，会换个参数再试一次。
    """
    try:
        args = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return f"参数不是合法的 JSON：{arguments}"

    func = TOOL_FUNCS.get(name)
    if func is None:
        return f"没有名为 {name} 的工具"

    try:
        return str(func(**args))
    except Exception as exc:  # noqa: BLE001 —— 这里就是要兜住所有异常
        return f"工具执行出错：{type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# 主循环：整个 Agent 的心跳
# ---------------------------------------------------------------------------
def run(user_input: str) -> None:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]
    total_in = total_out = 0

    for step in range(1, MAX_STEPS + 1):
        print(f"\n=== 第 {step} 轮：把 {len(messages)} 条消息发给模型 ===")

        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        if resp.usage:
            total_in += resp.usage.prompt_tokens
            total_out += resp.usage.completion_tokens

        msg = resp.choices[0].message

        # 把模型的回复（可能带 tool_calls）放回历史
        assistant = {"role": "assistant", "content": msg.content or ""}
        if msg.tool_calls:
            assistant["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        messages.append(assistant)

        # 没有工具调用 = 模型认为可以回答了，循环结束
        if not msg.tool_calls:
            print(f"\n最终回答：{msg.content}")
            break

        # 有工具调用 = 执行它们，把结果作为 tool 消息塞回去
        for tc in msg.tool_calls:
            print(f"  -> 模型请求：{tc.function.name}({tc.function.arguments})")
            result = run_tool(tc.function.name, tc.function.arguments)
            print(f"  <- 工具返回：{result}")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )
    else:
        print(f"\n达到最大轮数 {MAX_STEPS}，强制停止。")

    print(f"\n本次消耗：输入 {total_in} tokens，输出 {total_out} tokens")


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        question = "帮我算一下 23*47+8 是多少，再告诉我现在几点。"
    print(f"用户：{question}")
    run(question)
