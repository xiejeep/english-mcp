import asyncio
import os
from dotenv import load_dotenv
from openai import OpenAI

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
import mcp.server.stdio

# Load environment variables
load_dotenv()

# Configure OpenAI client for Deepseek-v3
client = OpenAI(
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# Store notes as a simple key-value dict to demonstrate state management
notes: dict[str, str] = {}

# Define the English coach role prompt
ENGLISH_COACH_ROLE = """You are my patient and supportive English speaking coach. Your task is to help me improve my oral expression by providing natural, context-appropriate alternatives when I struggle with vocabulary or sentence structures. Focus on daily conversations, cultural nuances, and idiomatic phrases.

交互规则

分步指导
根据我的描述，提供 2-3种地道表达，标注适用场景（正式/非正式）；若用户的描述涉及编程或代码审查场景，请提供符合职场和技术交流的专业表达，指出改进建议（例如性能优化、代码重构等具体方案）。

对比我的原始表达与优化版本，用表格说明差异（如：语法修正、更自然的用词或更专业的技术表述）。

场景化教学
若我未指定场景，默认提供旅行、社交、职场 三种场景的范例；但当涉及编程相关问题时，请使用适用于技术交流和代码审查的专业语言。

对俚语/习语补充文化背景（例如："'Break a leg' 是戏剧界祝福用语，日常中仅用于表演前").

错误处理
用 ✨ Friendly Tip: 开头指出我的语法/用词问题，或在技术表达中指出描述中的潜在问题。

扩展学习
每次回答后提供 1个相关短语 的延伸学习（例如：教 "make ends meet" 时补充 "tighten one's belt"），或者在编程场景下提供技术术语的延伸解释。

用 💡 Pro Tip: 标注母语者常用但教科书较少教的表达，特别是在技术讨论中，鼓励使用更精准、更专业的术语. """

server = Server("english-mcp")

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """
    List available note resources.
    Each note is exposed as a resource with a custom note:// URI scheme.
    """
    return [
        types.Resource(
            uri=AnyUrl(f"note://internal/{name}"),
            name=f"Note: {name}",
            description=f"A simple note named {name}",
            mimeType="text/plain",
        )
        for name in notes
    ]

@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> str:
    """
    Read a specific note's content by its URI.
    The note name is extracted from the URI host component.
    """
    if uri.scheme != "note":
        raise ValueError(f"Unsupported URI scheme: {uri.scheme}")

    name = uri.path
    if name is not None:
        name = name.lstrip("/")
        return notes[name]
    raise ValueError(f"Note not found: {name}")

@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    """
    List available prompts.
    Each prompt can have optional arguments to customize its behavior.
    """
    return [
        types.Prompt(
            name="summarize-notes",
            description="Creates a summary of all notes",
            arguments=[
                types.PromptArgument(
                    name="style",
                    description="Style of the summary (brief/detailed)",
                    required=False,
                )
            ],
        ),
        types.Prompt(
            name="/translate",
            description="Translate Chinese text to idiomatic English",
            arguments=[
                types.PromptArgument(
                    name="text",
                    description="Chinese text to translate",
                    required=True,
                )
            ],
        ),
        types.Prompt(
            name="/check",
            description="Check English grammar and provide improvement suggestions",
            arguments=[
                types.PromptArgument(
                    name="text",
                    description="English text to check",
                    required=True,
                )
            ],
        ),
        types.Prompt(
            name="/verify",
            description="Verify if English accurately represents Chinese meaning",
            arguments=[
                types.PromptArgument(
                    name="text",
                    description="English text followed by Chinese text (separated by '\\n中文:')",
                    required=True,
                )
            ],
        ),
        types.Prompt(
            name="/help",
            description="Display all available commands",
            arguments=[],
        ),
    ]

async def call_deepseek_api(prompt):
    """Helper function to call Deepseek-v3 API"""
    try:
        completion = client.chat.completions.create(
            model="deepseek-v3",
            messages=[
                {'role': 'system', 'content': ENGLISH_COACH_ROLE},
                {'role': 'user', 'content': prompt}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error calling Deepseek API: {str(e)}"

@server.get_prompt()
async def handle_get_prompt(
    name: str, arguments: dict[str, str] | None
) -> types.GetPromptResult:
    """
    Generate a prompt by combining arguments with server state.
    The prompt includes all current notes and can be customized via arguments.
    """
    arguments = arguments or {}
    
    if name == "summarize-notes":
        style = arguments.get("style", "brief")
        detail_prompt = " Give extensive details." if style == "detailed" else ""

        return types.GetPromptResult(
            description="Summarize the current notes",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"Here are the current notes to summarize:{detail_prompt}\n\n"
                        + "\n".join(
                            f"- {name}: {content}"
                            for name, content in notes.items()
                        ),
                    ),
                )
            ],
        )
    
    elif name == "/translate":
        text = arguments.get("text", "")
        if not text:
            return types.GetPromptResult(
                description="Translate Chinese to English",
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(
                            type="text",
                            text="Please provide Chinese text to translate."
                        ),
                    )
                ],
            )
        
        response = await call_deepseek_api(f"As my English coach, please translate the following Chinese text to natural, idiomatic English. Then follow our interaction rules to provide alternative expressions, usage scenarios, and learning tips: {text}")
        
        return types.GetPromptResult(
            description="Chinese to English Translation",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"Original Chinese: {text}"
                    ),
                ),
                types.PromptMessage(
                    role="assistant",
                    content=types.TextContent(
                        type="text",
                        text=response
                    ),
                )
            ],
        )
    
    elif name == "/check":
        text = arguments.get("text", "")
        if not text:
            return types.GetPromptResult(
                description="Check English grammar",
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(
                            type="text",
                            text="Please provide English text to check."
                        ),
                    )
                ],
            )
        
        response = await call_deepseek_api(f"Please check the grammar and phrasing of this English text and provide improvement suggestions: {text}")
        
        return types.GetPromptResult(
            description="English Grammar Check",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"Original text: {text}"
                    ),
                ),
                types.PromptMessage(
                    role="assistant",
                    content=types.TextContent(
                        type="text",
                        text=response
                    ),
                )
            ],
        )
    
    elif name == "/verify":
        text = arguments.get("text", "")
        if not text or "中文:" not in text:
            return types.GetPromptResult(
                description="Verify English translation",
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(
                            type="text",
                            text="Please provide the English text followed by Chinese text in the format: 'English text\\n中文:Chinese text'"
                        ),
                    )
                ],
            )
        
        parts = text.split("\n中文:", 1)
        english_text = parts[0].strip()
        chinese_text = parts[1].strip() if len(parts) > 1 else ""
        
        response = await call_deepseek_api(f"Please verify if this English text accurately expresses the meaning of the Chinese text:\n\nEnglish: {english_text}\n\nChinese: {chinese_text}")
        
        return types.GetPromptResult(
            description="Translation Verification",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"English: {english_text}\nChinese: {chinese_text}"
                    ),
                ),
                types.PromptMessage(
                    role="assistant",
                    content=types.TextContent(
                        type="text",
                        text=response
                    ),
                )
            ],
        )
    
    elif name == "/help":
        help_text = """Available commands:
- `/translate 中文文本` - Translate Chinese to idiomatic English
- `/check 英文文本` - Check English grammar and provide improvement suggestions
- `/verify 英文文本\n中文:中文文本` - Verify if English accurately expresses Chinese meaning
- `/help` - Display all available commands"""
        
        return types.GetPromptResult(
            description="Help Information",
            messages=[
                types.PromptMessage(
                    role="assistant",
                    content=types.TextContent(
                        type="text",
                        text=help_text
                    ),
                )
            ],
        )
    
    else:
        raise ValueError(f"Unknown prompt: {name}")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="add-note",
            description="Add a new note",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["name", "content"],
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can modify server state and notify clients of changes.
    """
    if name != "add-note":
        raise ValueError(f"Unknown tool: {name}")

    if not arguments:
        raise ValueError("Missing arguments")

    note_name = arguments.get("name")
    content = arguments.get("content")

    if not note_name or not content:
        raise ValueError("Missing name or content")

    # Update server state
    notes[note_name] = content

    # Notify clients that resources have changed
    await server.request_context.session.send_resource_list_changed()

    return [
        types.TextContent(
            type="text",
            text=f"Added note '{note_name}' with content: {content}",
        )
    ]

async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="english-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )