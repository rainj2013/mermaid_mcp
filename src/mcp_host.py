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
from mermaid_mcp_client import MermaidMCPClient

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
        
        capabilities = {
            "tools": [],
            "tools_details": [],
            "resources": [],
            "resources_details": [],
            "examples": {},
            "formats": {}
        }
        
        try:
            async with MermaidMCPClient(
                server_url=self.config["mcp_server"]["server_url"]
            ) as client:
                # 获取可用工具详情
                tools = await client.list_tools()
                capabilities["tools"] = [str(tool.name) for tool in tools]
                capabilities["tools_details"] = [
                    {
                        "name": str(tool.name),
                        "description": str(tool.description),
                        "input_schema": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                    }
                    for tool in tools
                ]
                logger.info(f"发现 {len(tools)} 个可用工具: {capabilities['tools']}")
                
                # 获取可用资源详情
                resources = await client.list_resources()
                capabilities["resources"] = [str(resource.uri) for resource in resources]
                capabilities["resources_details"] = [
                    {
                        "uri": str(resource.uri),
                        "name": str(resource.name),
                        "description": str(resource.description) if hasattr(resource, 'description') else ""
                    }
                    for resource in resources
                ]
                logger.info(f"发现 {len(resources)} 个可用资源: {capabilities['resources']}")
                
                # 获取示例
                capabilities["examples"] = await client.get_examples()
                
                # 获取支持的格式
                formats = await client.get_supported_formats()
                capabilities["formats"] = formats
                
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
            
            # 1. 分析用户意图和工具选择
            logger.info("分析用户意图和工具选择...")
            intent_result = await llm_client.analyze_tool_intent(
                user_input=user_input,
                available_tools=mcp_capabilities["tools_details"],
                available_resources=mcp_capabilities["resources_details"]
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
            
            # 2. 根据选择的工具执行相应操作
            if selected_tool == "render_mermaid":
                return await self._handle_mermaid_tool(user_input, mcp_capabilities, llm_client, intent_result)
            else:
                # 其他工具处理逻辑（可扩展）
                logger.warning(f"未实现的工具: {selected_tool}")
                return {
                    "success": False,
                    "is_chat": True,
                    "message": f"抱歉，工具 {selected_tool} 尚未实现",
                    "intent": intent_result
                }

    async def _handle_mermaid_tool(
        self, 
        user_input: str, 
        mcp_capabilities: Dict[str, Any], 
        llm_client, 
        intent_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        处理Mermaid图表生成工具
        
        Args:
            user_input: 用户输入文本
            mcp_capabilities: MCP Server能力信息
            llm_client: LLM客户端实例
            intent_result: 意图分析结果
            
        Returns:
            包含处理结果的字典
        """
        # 提取图表类型参数（如果有）
        tool_params = intent_result.get("tool_parameters", {})
        chart_type = tool_params.get("chart_type", "flowchart")
        
        # 生成Mermaid脚本
        logger.info(f"生成Mermaid脚本，图表类型: {chart_type}...")
        mermaid_script = await llm_client.generate_mermaid_script(
            user_input=user_input,
            chart_type=chart_type,
            examples=mcp_capabilities["examples"]
        )
        
        logger.info(f"生成Mermaid脚本完成，长度: {len(mermaid_script)} 字符")
        
        # 渲染图表
        logger.info("连接到MCP Server进行渲染...")
        async with MermaidMCPClient(
            server_url=self.config["mcp_server"]["server_url"]
        ) as client:
            
            # 验证脚本
            validation_result = await client.validate_mermaid(mermaid_script)
            if not validation_result.get("is_valid", False):
                logger.warning(f"Mermaid脚本验证失败: {validation_result.get('error')}")
                
                # 尝试修复脚本
                logger.info("尝试修复Mermaid脚本...")
                fixed_script = await llm_client.improve_mermaid_script(
                    mermaid_script, 
                    f"修复语法错误: {validation_result.get('error')}"
                )
                
                # 重新验证
                validation_result = await client.validate_mermaid(fixed_script)
                if validation_result.get("is_valid", False):
                    mermaid_script = fixed_script
                    logger.info("脚本修复成功")
                else:
                    return {
                        "success": False,
                        "is_chat": False,
                        "message": f"Mermaid脚本验证失败: {validation_result.get('error')}",
                        "script": mermaid_script,
                        "validation_error": validation_result.get('error')
                    }
            
            # 渲染图表
            render_result = await client.render_mermaid(
                mermaid_script,
                format="png",
                width=1920,
                height=1080
            )
            
            if render_result.get("success"):
                logger.info(f"图表渲染成功: {render_result.get('image_path')}")
                return {
                    "success": True,
                    "is_chat": False,
                    "message": "图表已成功生成！",
                    "intent": intent_result,
                    "script": mermaid_script,
                    "image_path": render_result.get("image_path"),
                    "file_id": render_result.get("file_id"),
                    "size": render_result.get("size")
                }
            else:
                logger.error(f"图表渲染失败: {render_result.get('error')}")
                return {
                    "success": False,
                    "is_chat": False,
                    "message": f"图表渲染失败: {render_result.get('error')}",
                    "script": mermaid_script,
                    "render_error": render_result.get("error")
                }
    
    async def interactive_mode(self):
        """交互模式"""
        print("🎮 Mermaid MCP Host - 智能聊天与图表生成器")
        print("=" * 50)
        print("💡 提示：可以聊天或生成图表，我会根据您的需求自动处理")
        print("   聊天：'今天吃什么好？'")
        print("   图表：'画一个用户登录的流程图，包含用户名密码验证'")
        print("=" * 50)
        
        try:
            # 分析MCP Server能力
            print("🔍 正在分析MCP Server能力...")
            mcp_capabilities = await self.analyze_mcp_capabilities()
            print(f"✅ MCP Server已就绪 - 支持 {len(mcp_capabilities['tools'])} 个工具")
            
            while True:
                try:
                    user_input = input("\n请输入您的问题或图表需求 (输入 'quit' 退出): ").strip()
                    
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
                            # 图表生成模式
                            print(f"\n✅ {result['message']}")
                            if "image_path" in result:
                                print(f"📁 文件路径: {result['image_path']}")
                            if "file_id" in result:
                                print(f"🆔 文件ID: {result['file_id']}")
                            if "size" in result:
                                print(f"📊 文件大小: {result['size']} bytes")
                            if "script" in result:
                                print(f"\n📝 生成的Mermaid脚本:")
                                print("-" * 30)
                                print(result["script"])
                    else:
                        print(f"\n❌ {result['message']}")
                        
                        if "script" in result:
                            print(f"\n📝 生成的脚本:")
                            print("-" * 30)
                            print(result["script"])
                        
                        # 提供改进建议
                        if "validation_error" in result:
                            print(f"\n💡 改进建议: 请检查Mermaid语法是否正确")
                        elif "render_error" in result:
                            print(f"\n💡 改进建议: 可能是脚本过于复杂或格式问题")
                        
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
            print("   1. MCP Server已启动: python src/mermaid_mcp_server.py")
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