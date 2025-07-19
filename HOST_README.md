# Mermaid MCP Host - 智能图表生成器

MCP Host 是一个智能化的Mermaid图表生成工具，它集成了月之暗面LLM API，能够理解用户的自然语言描述，自动生成对应的Mermaid图表。

## 功能特性

- 🧠 **智能意图识别**：使用月之暗面LLM自动识别用户的绘图意图
- 🎯 **自然语言处理**：支持用中文或英文描述图表需求
- 🔗 **MCP协议集成**：无缝集成MCP Server进行图表渲染
- 🛠️ **自动修复**：LLM自动修复语法错误的Mermaid脚本
- 🎨 **多图表类型**：支持流程图、时序图、类图、状态图等多种类型
- 💬 **交互式体验**：友好的命令行交互界面

## 快速开始

### 1. 安装依赖

使用 `uv` 安装项目依赖：

```bash
# 安装项目依赖
uv sync
```

### 2. 配置API密钥

1. 复制配置文件模板：
```bash
cp config.json.template config.json
```

2. 编辑 `config.json`，填入您的月之暗面API密钥：
```json
{
  "moonshot_api": {
    "api_key": "sk-xxxxxxxxxxxxxxxxxxxx",
    "base_url": "https://api.moonshot.cn/v1",
    "model": "moonshot-v1-8k"
  },
  "mcp_server": {
    "server_url": "http://127.0.0.1:8000/sse"
  }
}
```

### 3. 启动服务

1. **启动MCP Server**（在新终端）：
```bash
python src/mermaid_mcp_server.py
```

2. **启动MCP Host**（在另一个终端）：
```bash
python src/mcp_host.py
```

## 使用方法

### 交互模式

启动MCP Host后，您可以直接用自然语言描述图表需求：

```
🎮 Mermaid MCP Host - 智能图表生成器
==================================================
💡 提示：只需用自然语言描述您想要的图表，我会自动生成
   例如：'画一个用户登录的流程图，包含用户名密码验证'
==================================================

请输入您想要的图表描述 (输入 'quit' 退出): 
```

### 使用示例

#### 示例1：流程图
```
请输入您想要的图表描述: 画一个用户注册流程图，包括邮箱验证、密码设置和个人信息填写
```

#### 示例2：时序图
```
请输入您想要的图表描述: 创建一个电商订单处理的时序图，包含用户、订单系统、支付网关和库存管理
```

#### 示例3：类图
```
请输入您想要的图表描述: 设计一个学生管理系统的类图，包含学生、课程、教师和成绩类
```

#### 示例4：状态图
```
请输入您想要的图表描述: 绘制订单状态的状态图，从待付款到已发货的各个状态
```

## 支持的图表类型

MCP Host 支持以下Mermaid图表类型：

- **流程图 (flowchart)**：展示流程和决策路径
- **时序图 (sequence)**：展示对象间的交互序列
- **类图 (class)**：展示类之间的关系
- **状态图 (state)**：展示对象状态变化
- **实体关系图 (entity)**：展示数据库实体关系
- **甘特图 (gantt)**：展示项目时间线
- **用户旅程图 (user-journey)**：展示用户体验流程

## 高级用法

### 编程接口

您可以在自己的代码中使用MCP Host：

```python
import asyncio
from src.mcp_host import MCPHost


async def main():
   host = MCPHost("src/config.json")

   # 分析MCP Server能力
   capabilities = await host.analyze_mcp_capabilities()

   # 处理用户输入
   result = await host.process_user_input(
      "创建一个简单的登录流程图，包含用户名密码验证",
      capabilities
   )

   if result["success"]:
      print(f"图表已生成: {result['image_path']}")
      print(f"Mermaid脚本:\n{result['script']}")


if __name__ == "__main__":
   asyncio.run(main())
```

### 批量处理

```python
import asyncio
from src.mcp_host import MCPHost


async def batch_process():
   host = MCPHost("src/config.json")
   capabilities = await host.analyze_mcp_capabilities()

   descriptions = [
      "用户注册流程图",
      "订单处理时序图",
      "数据库实体关系图"
   ]

   for desc in descriptions:
      result = await host.process_user_input(desc, capabilities)
      if result["success"]:
         print(f"✅ {desc}: {result['image_path']}")


asyncio.run(batch_process())
```

## 配置说明

### 配置文件结构

`config.json` 文件包含以下配置项：

```json
{
  "moonshot_api": {
    "api_key": "您的月之暗面API密钥",
    "base_url": "https://api.moonshot.cn/v1",
    "model": "moonshot-v1-8k"
  },
  "mcp_server": {
    "server_url": "http://127.0.0.1:8000/sse"
  },
  "host_settings": {
    "log_level": "INFO",
    "max_retries": 3,
    "timeout": 30
  }
}
```

### 获取月之暗面API密钥

1. 访问 [月之暗面开放平台](https://platform.moonshot.cn)
2. 注册账号并完成实名认证
3. 创建API密钥
4. 将密钥填入 `config.json` 的 `moonshot_api.api_key` 字段

## 故障排除

### 常见问题

1. **API密钥错误**
   ```
   ❌ API错误 401: Invalid authentication credentials
   ```
   **解决：** 检查 `config.json` 中的API密钥是否正确

2. **MCP Server未启动**
   ```
   ❌ Failed to connect to MCP server
   ```
   **解决：** 先启动MCP Server: `python src/mermaid_mcp_server.py`

3. **网络连接问题**
   ```
   ❌ 网络请求失败: Cannot connect to host
   ```
   **解决：** 检查网络连接和防火墙设置

4. **图表类型识别错误**
   ```
   ❌ 生成的图表类型不符合预期
   ```
   **解决：** 在描述中明确指定图表类型，如"创建一个**流程图**"或"绘制**时序图**"

### 查看日志

查看详细日志信息：
```bash
tail -f mcp_host.log
```

## 项目结构

```
mermaid_mcp/
├── src/
│   ├── mcp_host.py          # MCP Host主程序
│   ├── llm_client.py        # 月之暗面LLM客户端
│   ├── mermaid_mcp_client.py # MCP客户端
│   └── mermaid_mcp_server.py # MCP服务器
├── config.json.template    # 配置文件模板
├── config.json             # 用户配置文件
├── HOST_README.md          # 本文档
└── mcp_host.log           # 运行日志
```

## 开发指南

### 扩展功能

1. **添加新的图表类型**：修改 `llm_client.py` 中的图表类型识别逻辑
2. **改进提示词**：调整 `llm_client.py` 中的系统提示词以获得更好的结果
3. **集成其他LLM**：可以扩展 `llm_client.py` 支持其他LLM提供商

### 贡献代码

欢迎提交 Issue 和 Pull Request！在贡献代码前，请确保：

1. 代码符合 PEP 8 规范
2. 添加适当的错误处理
3. 更新相关文档
4. 测试所有功能

## 许可证

本项目采用 MIT 许可证，详见 LICENSE 文件。

## 支持

- 📧 问题反馈：提交 GitHub Issue
- 📖 文档更新：欢迎贡献改进文档
- 💡 功能建议：欢迎提出新的功能想法