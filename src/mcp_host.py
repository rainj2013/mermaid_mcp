#!/usr/bin/env python3
"""
MCP Host - Mermaid MCP 智能主机

智能分析用户意图并自动生成Mermaid图表的主机程序。
集成月之暗面LLM API实现自然语言理解，自动调用MCP Server进行图表渲染。
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path

from llm_client import MoonshotClient
from mcp_client_wrapper import MCPClientWrapper
from mermaid_mcp_client import MermaidMCPClient  # 仅用于Mermaid特定server

# 配置日志
import logging.handlers

project_root = Path(__file__).parent.parent
log_dir = project_root / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "mcp_host.log"

# 创建自定义logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 清除现有的处理器
logger.handlers.clear()

# 创建文件处理器
file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# 创建控制台处理器
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# 添加处理器到logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# 测试日志
logger.info("=== MCP Host 日志系统初始化完成 ===")
logger.debug(f"日志文件路径: {log_file}")
logger.debug(f"日志文件是否存在: {log_file.exists()}")
logger.debug(f"日志目录权限: {log_dir.stat()}")

class MCPHost:
    """MCP Host 主类"""
    
    def __init__(self, config_path: str = None):
        """
        初始化MCP Host
        
        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
        """
        if config_path is None:
            # 使用项目根目录下的config目录中的配置文件
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config" / "config.json"
        else:
            config_path = Path(config_path)
        self.config_path = config_path
        self.config = self._load_config()
        self.llm_client = None
        self.mcp_client = None
        logger.info(f"MCPHost 初始化完成，配置文件路径: {self.config_path}")
        
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        config_file = Path(self.config_path)
        
        if not config_file.exists():
            # 使用模板文件
            project_root = Path(__file__).parent.parent
            template_file = project_root / "config" / "config.json.template"
            if template_file.exists():
                logger.warning(f"配置文件 {self.config_path} 不存在，使用模板文件")
                with open(template_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                raise FileNotFoundError(
                    f"配置文件 {self.config_path} 和模板文件 {template_file} 都不存在"
                )
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # 验证必要的配置
            if not config.get('moonshot_api', {}).get('api_key'):
                raise ValueError("请在配置文件中设置 moonshot_api.api_key")
                
            return config
            
        except json.JSONDecodeError as e:
            raise ValueError(f"配置文件格式错误: {e}")
    
    async def analyze_mcp_capabilities(self) -> Dict[str, Any]:
        """
        分析MCP Server的能力和可用资源
        
        Returns:
            包含MCP Server信息的字典，包含完整的工具和资源详情
        """
        logger.info("正在分析MCP Server能力...")
        
        try:
            # 使用通用MCP客户端包装器
            async with MCPClientWrapper(
                server_url=self.config["mcp_server"]["server_url"],
                client_class=MermaidMCPClient
            ) as client:
                capabilities = await client.get_capabilities()
                
        except Exception as e:
            logger.error(f"分析MCP Server能力失败: {e}")
            raise
            
        return capabilities
    
    async def process_user_input(self, user_input: str, mcp_capabilities: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理用户输入，智能选择工具或直接聊天回复
        
        Args:
            user_input: 用户输入文本
            mcp_capabilities: MCP Server能力信息
            
        Returns:
            包含处理结果的字典
        """
        logger.info(f"开始处理用户输入: {user_input[:50]}...")
        
        async with MoonshotClient(
            api_key=self.config["moonshot_api"]["api_key"],
            base_url=self.config["moonshot_api"]["base_url"],
            model=self.config["moonshot_api"]["model"]
        ) as llm_client:
            
            # 使用通用MCP客户端包装器
            async with MCPClientWrapper(
                server_url=self.config["mcp_server"]["server_url"],
                client_class=MermaidMCPClient
            ) as mcp_client:
                
                # 1. 分析用户意图和工具选择
                logger.info("分析用户意图和工具选择...")
                intent_result = await llm_client.analyze_tool_intent(
                    user_input=user_input,
                    available_tools=mcp_capabilities["tools"],
                    available_resources=mcp_capabilities["resources"]
                )
                
                if not intent_result.get("requires_tool", False):
                    # 不需要使用工具，直接聊天回复
                    logger.info("处理为通用聊天...")
                    
                    # 优先使用工具分析的回复，如果没有则调用chat_with_user
                    if intent_result.get("direct_response"):
                        chat_response = intent_result["direct_response"]
                        logger.info(f"工具分析直接回复: {chat_response}")
                    else:
                        chat_response = await llm_client.chat_with_user(user_input)
                    
                    return {
                        "success": True,
                        "is_chat": True,
                        "message": chat_response,
                        "intent": intent_result
                    }
                
                selected_tool = intent_result.get("selected_tool", "")
                logger.info(f"检测到工具使用需求，选择工具: {selected_tool}，置信度: {intent_result.get('confidence', 0)}")
                
                # 2. 找到选中的工具定义
                selected_tool_def = None
                for tool in mcp_capabilities["tools"]:
                    if tool["name"] == selected_tool:
                        selected_tool_def = tool
                        break
                
                if not selected_tool_def:
                    return {
                        "success": False,
                        "is_chat": False,
                        "message": f"未找到工具 {selected_tool}",
                        "intent": intent_result
                    }
                
                # 3. 使用LLM提供的参数，LLM负责所有参数组装
                final_params = intent_result.get("tool_parameters", {})
                logger.info(f"使用LLM提供的参数: {final_params}")
                
                logger.info(f"最终工具参数: {final_params}")
                
                # 4. 执行选择的工具
                try:
                    result = await mcp_client.execute_tool(selected_tool, final_params)
                    
                    # 构建通用的工具执行响应
                    response_data = {
                        "success": True,
                        "is_chat": False,
                        "message": f"工具 {selected_tool} 执行成功！",
                        "intent": intent_result,
                        "tool_name": selected_tool,
                        "tool_result": result  # 直接传递完整的工具结果
                    }
                    
                    return response_data
                    
                except Exception as e:
                    logger.error(f"执行工具 {selected_tool} 失败: {e}")
                    error_response = {
                        "success": False,
                        "is_chat": False,
                        "message": f"执行工具失败: {e}",
                        "intent": intent_result,
                        "error": str(e),
                        "tool_parameters": final_params  # 包含参数用于调试
                    }
                    
                    return error_response

    
    async def interactive_mode(self):
        """交互模式"""
        print("🎮 MCP Host - 智能工具调用助手")
        print("=" * 50)
        print("💡 提示：我可以帮您调用各种可用工具")
        print("   聊天：直接提问或描述需求")
        print("   工具：描述您需要使用的功能")
        print("=" * 50)
        
        try:
            # 分析MCP Server能力
            print("🔍 正在分析MCP Server能力...")
            mcp_capabilities = await self.analyze_mcp_capabilities()
            print(f"✅ MCP Server已就绪 - 发现 {len(mcp_capabilities['tools'])} 个可用工具")
            
            while True:
                try:
                    user_input = input("\n请输入您的问题或需求 (输入 'quit' 退出): ").strip()
                    
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        print("👋 感谢使用！再见！")
                        break
                    
                    if not user_input:
                        continue
                    
                    # 处理用户输入
                    result = await self.process_user_input(user_input, mcp_capabilities)
                    
                    if result["success"]:
                        if result.get("is_chat", False):
                            # 通用聊天模式
                            print(f"\n🤖 {result['message']}")
                        else:
                            # 工具执行成功模式
                            print(f"\n✅ {result['message']}")
                            
                            # 通用结果展示 - 不依赖特定工具字段
                            tool_result = result.get("tool_result", {})
                            if isinstance(tool_result, dict):
                                # 显示工具返回的所有信息
                                for key, value in tool_result.items():
                                    if key == "success":
                                        continue  # 跳过success标志
                                    elif isinstance(value, str) and len(value) > 100:
                                        # 长内容截断显示
                                        print(f"📋 {key}: {value[:100]}...")
                                    else:
                                        print(f"📋 {key}: {value}")
                            
                            # 显示参数信息
                            if "intent" in result and "tool_parameters" in result["intent"]:
                                params = result["intent"]["tool_parameters"]
                                if params:
                                    print(f"\n📝 工具参数:")
                                    print("-" * 30)
                                    for key, value in params.items():
                                        if isinstance(value, str) and len(value) > 100:
                                            print(f"{key}: {value[:100]}...")
                                        else:
                                            print(f"{key}: {value}")
                    else:
                        print(f"\n❌ {result['message']}")
                        
                        # 显示错误详情
                        if "error" in result:
                            print(f"💬 错误详情: {result['error']}")
                        
                        # 显示参数用于调试
                        if "tool_parameters" in result:
                            params = result["tool_parameters"]
                            if params:
                                print(f"\n📝 使用的参数:")
                                print("-" * 30)
                                for key, value in params.items():
                                    if isinstance(value, str) and len(value) > 100:
                                        print(f"{key}: {value[:100]}...")
                                    else:
                                        print(f"{key}: {value}")
                        
                        # 提供通用建议
                        if "validation_error" in result or "render_error" in result:
                            print(f"\n💡 建议: 请检查输入参数是否正确，或联系技术支持")
                        
                except KeyboardInterrupt:
                    print("\n👋 用户中断，再见！")
                    break
                except Exception as e:
                    logger.error(f"交互模式错误: {e}")
                    print(f"❌ 发生错误: {e}")
                    
        except Exception as e:
            logger.error(f"启动失败: {e}")
            print(f"❌ 启动失败: {e}")
            print("💡 请确保：")
            print("   1. MCP Server已启动")
            print("   2. 配置文件config.json已正确设置")
            print("   3. 月之暗面API密钥已配置")

async def main():
    """主函数"""
    logger.info("开始执行主函数")
    try:
        # 检查配置文件
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config" / "config.json"
        if not config_path.exists():
            logger.error(f"配置文件 {config_path} 不存在")
            print(f"⚠️ 配置文件 {config_path} 不存在")
            print("📋 请复制 config.json.template 为 config/config.json 并填入您的API密钥")
            return
        
        logger.info(f"使用配置文件: {config_path}")
        host = MCPHost(config_path)
        
        # 检查命令行参数
        if len(sys.argv) > 1 and sys.argv[1] == "--cli":
            logger.info("使用CLI模式启动")
            await host.interactive_mode()
        else:
            logger.info("使用默认交互模式启动")
            await host.interactive_mode()
    except Exception as e:
        logger.exception(f"主函数执行失败: {e}")
        raise

if __name__ == "__main__":
    logger.info("=== MCP Host 程序启动 ===")
    asyncio.run(main())