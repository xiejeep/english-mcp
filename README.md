# english-mcp MCP server

写代码学英语

## Components

### Resources

The server implements a simple note storage system with:
- Custom note:// URI scheme for accessing individual notes
- Each note resource has a name, description and text/plain mimetype

### Slash Commands

The server provides several slash commands for English learning:
- `/translate 中文文本` - Translate Chinese to idiomatic English
- `/check 英文文本` - Check English grammar and provide improvement suggestions
- `/verify 英文文本\n中文:中文文本` - Verify if English accurately expresses Chinese meaning
- `/help` - Display all available commands

### Prompts

The server provides a single prompt:
- summarize-notes: Creates summaries of all stored notes
  - Optional "style" argument to control detail level (brief/detailed)
  - Generates prompt combining all current notes with style preference

### Tools

The server implements one tool:
- add-note: Adds a new note to the server
  - Takes "name" and "content" as required string arguments
  - Updates server state and notifies clients of resource changes

## Configuration

To use this service, you need to configure the API Key for Aliyun's Deepseek-v3 model.

1. Get an API Key from [Aliyun Model Studio](https://help.aliyun.com/zh/model-studio/developer-reference/get-api-key)
2. Set your API key in the `.env` file: `DASHSCOPE_API_KEY=your-dashscope-api-key-here`

## Quickstart

### Install

#### Claude Desktop

On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`
On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

<details>
  <summary>Development/Unpublished Servers Configuration</summary>
  ```
  "mcpServers": {
    "english-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/jmspay/Desktop/weather_service",
        "run",
        "english-mcp"
      ]
    }
  }
  ```
</details>

<details>
  <summary>Published Servers Configuration</summary>
  ```
  "mcpServers": {
    "english-mcp": {
      "command": "uvx",
      "args": [
        "english-mcp"
      ]
    }
  }
  ```
</details>

## Development

### Building and Publishing

To prepare the package for distribution:

1. Sync dependencies and update lockfile:
```bash
uv sync
```

2. Build package distributions:
```bash
uv build
```

This will create source and wheel distributions in the `dist/` directory.

3. Publish to PyPI:
```bash
uv publish
```

Note: You'll need to set PyPI credentials via environment variables or command flags:
- Token: `--token` or `UV_PUBLISH_TOKEN`
- Or username/password: `--username`/`UV_PUBLISH_USERNAME` and `--password`/`UV_PUBLISH_PASSWORD`

### Debugging

Since MCP servers run over stdio, debugging can be challenging. For the best debugging
experience, we strongly recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector).


You can launch the MCP Inspector via [`npm`](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) with this command:

```bash
npx @modelcontextprotocol/inspector uv --directory /Users/jmspay/Desktop/weather_service run english-mcp
```


Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.

## 斜杠命令使用说明

本服务支持使用斜杠命令来执行不同操作。以下是一些常用命令及其用法说明：

- `/translate 中文文本`
  - 功能：将中文文本翻译成地道的英文，同时根据英语教练交互规则提供替代表达、场景示例、语法提示和延伸学习建议。
  - 用法示例：
    ```
    /translate 你在他乡还好吗
    ```
  - 注意：请确保在命令后有空格，再输入需要翻译的中文文本。

- `/check 英文文本`
  - 功能：检查英文文本的语法和用词，并提供改进建议。
  - 用法示例：
    ```
    /check I has a apple.
    ```

- `/summarize-notes`
  - 功能：总结当前的笔记。可根据参数提供详细或简要的总结。
  - 用法示例：
    ```
    /summarize-notes style=detailed
    ```

- `/help`
  - 功能：显示所有可用的斜杠命令和它们的说明。
  - 用法示例：
    ```
    /help
    ```

调用这些斜杠命令时，系统会自动将预设的角色信息（如英语教练角色 ENGLISH_COACH_ROLE）注入到请求的上下文中，从而确保返回的信息符合预期的交互规则。