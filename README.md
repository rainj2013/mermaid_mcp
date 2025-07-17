# mermaid_mcp
一个基于mermaid-cli的绘图MCP工具

## 安装与运行

1. **克隆项目**
   ```bash
   git clone https://github.com/rainj2013/mermaid_mcp.git
   cd mermaid_mcp
   ```

2. **安装 uv（推荐）**
   
   本项目推荐使用 [uv](https://github.com/astral-sh/uv) 来管理Python依赖，它比pip更快、更可靠。
   
   **macOS/Linux:**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   
   **Windows:**
   ```bash
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
   
   **使用pip安装:**
   ```bash
   pip install uv
   ```

3. **安装依赖**
   ```bash
   uv sync
   ```
   
   > 💡 `uv sync` 会自动读取 `pyproject.toml` 文件并安装所有依赖，同时创建虚拟环境。

4. **全局安装 mermaid-cli**
   ```bash
   npm install -g @mermaid-js/mermaid-cli --ignore-scripts
   ```
   
   > ⚠️ 使用 `--ignore-scripts` 参数跳过浏览器安装，因为我们会使用本地浏览器。

5. **配置 puppeteer-config.json**
   
   `src/puppeteer-config.json` 文件中的 `executablePath` 字段需要填写您本地 Chrome 或 Chromium 浏览器的实际路径，否则渲染会失败。
   
   示例：
   ```json
   {
     "executablePath": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
   }
   ```
   
   > ⚠️ 请根据您的操作系统和浏览器实际安装位置进行修改。

6. **运行服务**

   **方式一：使用 fastmcp 运行**
   ```bash
   fastmcp run src/mermaid_mcp_server.py
   ```

   **方式二：直接使用 Python 运行**
   ```bash
   python src/mermaid_mcp_server.py
   ```
   
   默认监听 8000 端口。
