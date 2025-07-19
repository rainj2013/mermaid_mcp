# Mermaid MCP Client

一个基于 MCP 协议的 Mermaid 图形渲染客户端，用于与 Mermaid MCP Server 交互，实现图形渲染和语法验证功能。

## 功能特性

- 🔗 **MCP 协议支持**：基于 FastMCP 客户端实现，支持 HTTP/SSE 传输
- 🎨 **多种输出格式**：支持 PNG、SVG、PDF 等多种图形格式
- ✅ **语法验证**：实时验证 Mermaid 语法正确性
- 🖥️ **交互模式**：提供友好的命令行交互界面
- 📋 **资源管理**：支持查看服务器工具、资源和示例
- 🔍 **详细日志**：完整的操作日志记录，便于调试和追踪

## 安装与配置

### 1. 环境要求

- Python 3.12+
- 已安装 [Mermaid MCP Server](../README.md)
- 已配置好 mermaid-cli 和 puppeteer

### 2. 安装依赖

使用 `uv` 安装项目依赖：

```bash
# 安装项目依赖
uv sync
```

### 3. 启动服务器

在运行客户端之前，确保 Mermaid MCP Server 已启动：

```bash
# 方式一：使用 fastmcp
fastmcp run src/mermaid_mcp_server.py

# 方式二：直接使用 Python
python src/mermaid_mcp_server.py
```

服务器默认监听 `http://127.0.0.1:8000/sse`

## 使用方法

### 1. 交互模式

运行客户端进入交互模式：

```bash
python src/mermaid_mcp_client.py
```

交互模式下支持的命令：

- `render` - 渲染 Mermaid 图形
- `validate` - 验证 Mermaid 语法
- `formats` - 查看支持的输出格式
- `examples` - 显示示例图形
- `tools` - 列出可用工具
- `resources` - 列出可用资源
- `help` - 显示帮助信息
- `quit` - 退出程序

### 2. 编程接口

```python
import asyncio
from src.mermaid_mcp_client import MermaidMCPClient

async def main():
    async with MermaidMCPClient() as client:
        # 渲染图形
        result = await client.render_mermaid('''
            graph TD
                A[Start] --> B[Process]
                B --> C[End]
        ''', format='png')
        
        if result.get('success'):
            print(f"图形已保存到: {result['image_path']}")
        else:
            print(f"渲染失败: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(main())
```

## API 参考

### MermaidMCPClient 类

#### 构造函数

```python
client = MermaidMCPClient(server_url="http://127.0.0.1:8000/sse")
```

**参数：**
- `server_url` (str): MCP 服务器地址，默认 `http://127.0.0.1:8000/sse`

#### 主要方法

##### `render_mermaid(script, format='png', width=800, height=600, background='transparent')`

渲染 Mermaid 图形为图片。

**参数：**
- `script` (str): Mermaid 脚本内容
- `format` (str): 输出格式，可选值：`png`, `svg`, `pdf`
- `width` (int): 图片宽度，默认 800
- `height` (int): 图片高度，默认 600
- `background` (str): 背景颜色，默认 `transparent`

**返回值：**
```python
{
    "success": bool,
    "image_path": str,  # 生成的图片路径
    "file_id": str,     # 文件唯一标识
    "size": int         # 文件大小(字节)
}
```

##### `validate_mermaid(script)`

验证 Mermaid 脚本语法。

**参数：**
- `script` (str): Mermaid 脚本内容

**返回值：**
```python
{
    "is_valid": bool,   # 语法是否正确
    "error": str        # 错误信息(如果有)
}
```

##### `get_supported_formats()`

获取服务器支持的输出格式列表。

**返回值：**
```python
{
    "formats": ["png", "svg", "pdf"],
    "descriptions": {
        "png": "PNG image format",
        "svg": "SVG vector format",
        "pdf": "PDF document format"
    },
    "default": "png"
}
```

##### `get_examples()`

获取示例 Mermaid 脚本。

**返回值：**
```python
{
    "flowchart": "graph TD\n    A[Start] --> B[Process]\n    ...",
    "sequence": "sequenceDiagram\n    Alice->>Bob: Hello\n    ..."
}
```

##### `list_tools()` 和 `list_resources()`

列出服务器提供的工具和资源。

##### `get_output_directory()` 和 `get_cli_path()`

获取服务器配置信息。

## 示例代码

### 基本图形渲染

```python
async def render_basic_flowchart():
    async with MermaidMCPClient() as client:
        script = '''
            graph TD
                A[用户登录] --> B{验证成功?}
                B -->|是| C[进入主页]
                B -->|否| D[显示错误]
                C --> E[完成]
                D --> F[重新登录]
        '''
        
        result = await client.render_mermaid(script, format='png')
        if result.get('success'):
            print(f"流程图已保存: {result['image_path']}")
```

### 语法验证

```python
async def validate_mermaid_script():
    async with MermaidMCPClient() as client:
        script = '''
            sequenceDiagram
                Alice->>Bob: Hello
                Bob-->>Alice: Hi!
        '''
        
        result = await client.validate_mermaid(script)
        if result.get('is_valid'):
            print("✅ Mermaid 语法正确")
        else:
            print(f"❌ 语法错误: {result.get('error')}")
```

### 批量渲染

```python
async def batch_render():
    diagrams = [
        {
            "name": "user_flow",
            "script": "graph TD\n    A[登录] --> B[主页]\n    B --> C[退出]",
            "format": "png"
        },
        {
            "name": "system_arch",
            "script": "graph LR\n    Web[Web服务器] --> App[应用服务器]\n    App --> DB[数据库]",
            "format": "svg"
        }
    ]
    
    async with MermaidMCPClient() as client:
        for diagram in diagrams:
            result = await client.render_mermaid(
                diagram["script"], 
                format=diagram["format"]
            )
            if result.get('success'):
                print(f"✅ {diagram['name']}: {result['image_path']}")
```

## 故障排除

### 连接问题

1. **服务器未启动**
   ```
   ❌ Failed to connect: [Errno 111] Connection refused
   ```
   **解决：** 启动服务器：
   ```bash
   python src/mermaid_mcp_server.py
   ```

2. **端口被占用**
   ```
   ❌ Failed to connect: [Errno 98] Address already in use
   ```
   **解决：** 修改服务器端口或关闭占用端口的程序

3. **网络连接问题**
   ```
   ❌ Failed to connect: Connection timeout
   ```
   **解决：** 检查防火墙设置，确保允许端口 8000 的连接

### 渲染问题

1. **mermaid-cli 未找到**
   ```
   ❌ Error: mmdc command not found
   ```
   **解决：** 全局安装 mermaid-cli：
   ```bash
   npm install -g @mermaid-js/mermaid-cli --ignore-scripts
   ```

2. **浏览器路径配置错误**
   ```
   ❌ Error: Chromium not found
   ```
   **解决：** 检查 `src/puppeteer-config.json` 中的 `executablePath` 设置

3. **语法错误**
   ```
   ❌ 解析失败: Parse error on line 3
   ```
   **解决：** 使用 `validate` 命令检查语法，或参考 `examples` 中的示例

### 查看日志

客户端日志保存在 `src/mcp_client.log` 中，可通过查看日志获取详细的错误信息：

```bash
tail -f src/mcp_client.log
```

## 开发指南

### 项目结构

```
mermaid_mcp/
├── src/
│   ├── mermaid_mcp_client.py    # 客户端主程序
│   └── mermaid_mcp_server.py    # 服务器程序
├── output/                      # 生成的图形文件
├── mcp_client_README.md        # 本说明文档
└── pyproject.toml              # 项目配置
```

### 扩展功能

可以通过以下方式扩展客户端功能：

1. **添加新的命令**：在 `interactive_mode()` 函数中添加新命令处理
2. **自定义输出格式**：扩展 `render_mermaid()` 方法支持更多参数
3. **集成到应用**：将客户端类集成到其他 Python 应用中
