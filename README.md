# Hello Agent

一个 **150 行、不依赖任何 Agent 框架** 的最小 Agent。

它只做一件事：让模型自己决定「回答」还是「调工具」，然后把工具结果喂回去，直到它给出答案。

> 所有框架（LangGraph / AutoGen / Coze）都是这个循环的包装。
> 先把这个跑通、读懂、改坏，你再看框架就不会被名词唬住。

---

## 一、跑起来（5 分钟）

### 1. 装 Python 和 uv

- Python 3.10+：<https://www.python.org/downloads/>（安装时勾选 **Add to PATH**）
- uv：<https://docs.astral.sh/uv/>

装完开 PowerShell 验证：

```powershell
python --version
uv --version
```

### 2. 填 API Key

去 <https://platform.deepseek.com> 注册 → 充值 10 元 → 创建 API Key。

```powershell
cd hello-agent
copy .env.example .env
notepad .env
```

把 `sk-在这里填你的key` 换成你自己的 key，保存。

### 3. 运行

**方式 A：用 uv（推荐，需先装 uv）**

```powershell
uv sync
uv run python main.py "帮我算一下 23*47+8，再告诉我现在几点"
```

**方式 B：系统 Python + venv（不装 uv 也能跑）**

如果你电脑上已经有 Python 3.12 和 pip，这条路更省事：

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install openai python-dotenv
python main.py "帮我算一下 23*47+8，再告诉我现在几点"
```

下次再跑，只需：

```powershell
cd hello-agent
.\.venv\Scripts\activate
python main.py "你的问题"
```

如果看到类似下面的输出，就成功了：

```
用户：帮我算一下 23*47+8，再告诉我现在几点

=== 第 1 轮：把 2 条消息发给模型 ===
  -> 模型请求：calculator({"expression": "23*47+8"})
  <- 工具返回：1089

=== 第 2 轮：把 4 条消息发给模型 ===
  -> 模型请求：get_current_time({})
  <- 工具返回：2026-11-03 02:45:10

=== 第 3 轮：把 6 条消息发给模型 ===

最终回答：23*47+8 = 1089。当前时间是 2026-11-03 02:45:10。

本次消耗：输入 412 tokens，输出 58 tokens
```

**注意看每一轮的「消息条数」在变多**——这就是 Agent 的全部秘密：历史在累积。

---

## 二、怎么读这份代码（别从头读到尾）

按这个顺序读，40 分钟够：

| 顺序 | 位置 | 你在看什么 |
|---|---|---|
| 1 | `def run()` 里的 `for step in range(...)` | **主循环**，全文件最重要的 20 行 |
| 2 | `messages.append(assistant)` 附近 | 模型说了什么，怎么记进历史 |
| 3 | `for tc in msg.tool_calls:` 这一段 | 工具结果怎么塞回去 |
| 4 | `run_tool()` | 为什么异常要变成字符串返回，而不是崩掉 |
| 5 | `TOOLS` 里的 JSON Schema | 模型怎么知道"有这个工具" |
| 6 | `calculator` / `save_note` | 工具就是普通函数，没什么神秘 |

**一句话总结**：Agent = 大模型 + 一个 while 循环 + 一堆普通函数。

---

## 三、五个练习（由易到难，做完才算入门）

### 练习 1｜改人设（10 分钟）
把 `SYSTEM_PROMPT` 改成「你是一个只说英文的助手」，重新运行。
观察：同样的输入，行为和输出有什么变化？

### 练习 2｜加一个工具（30 分钟）
加一个 `get_weather(city)`，返回假数据即可（比如"晴，22 度"）。
- 在 `TOOLS` 里加定义
- 写一个普通函数
- 注册进 `TOOL_FUNCS`

然后问它「合肥今天天气怎么样」。
**重点观察**：它会不会调用工具？如果不会，多半是 `description` 写得太模糊。

### 练习 3｜故意让它出错（20 分钟）
问它 `1/0`。看 `run_tool` 怎么把 `ZeroDivisionError` 变成字符串，模型看到之后怎么反应。

**这就是 Agent 的"自我修复"**——也是它比普通程序难调试的原因。

### 练习 4｜加记忆（1 小时）
现在每次启动都是失忆的。改成：
- 启动时读 `notes.md`，把内容拼进 `SYSTEM_PROMPT`
- 这样它就能记住上次让你存的东西

做完你会真正理解「记忆」不是一个玄学功能，就是一个文件。

### 练习 5｜删掉保护（10 分钟）
把 `MAX_STEPS` 改成 `1`，再问一个需要两步的问题。
看它会发生什么——**这就是为什么所有 Agent 框架都要有"最大轮数"和"停止条件"**。

---

## 四、常见报错

| 报错 | 原因 | 解决 |
|---|---|---|
| `没有找到 DEEPSEEK_API_KEY` | 没有 `.env` 或没填 key | 复制 `.env.example` 为 `.env` 并填入 |
| `AuthenticationError` / 401 | key 错了或余额为 0 | 去平台检查 key 和余额 |
| `ModuleNotFoundError: openai` | 没装依赖 | 在 hello-agent 目录下执行 `uv sync` |
| 中文乱码 | 控制台编码 | 代码里已处理；仍乱码就用 Windows Terminal |
| `uv: 无法识别` | uv 没装或没进 PATH | 重装 uv，重开终端 |

---

## 五、跑通之后去哪

这个文件跑通、改坏、修好之后，你已经具备了：

- 调 API、流式、工具调用
- 理解 agent loop、错误回传、停止条件
- 知道"框架"到底封装了什么

接下来才是：RAG（第 5 周）、LangGraph（第 7 周）、MCP（第 7 周）。

**顺序别反。** 先有这 150 行，后面的东西才有地基。
