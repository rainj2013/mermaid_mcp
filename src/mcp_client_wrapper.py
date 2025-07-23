"""
通用MCP客户端包装器
支持任意MCP server，不依赖特定实现
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class MCPClientWrapper:
    """通用MCP客户端包装器，支持任意MCP server"""
    
    def __init__(self, server_url: str, client_class):
        """
        初始化通用MCP客户端
        
        Args:
            server_url: MCP server URL
            client_class: MCP客户端类（如MermaidMCPClient）
        """
        self.server_url = server_url
        self.client_class = client_class
        self.client = None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.client = await self.client_class(self.server_url).__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.client:
            await self.client.__aexit__(exc_type, exc_val, exc_tb)
            
    async def get_capabilities(self) -> Dict[str, Any]:
        """获取MCP server的所有能力"""
        try:
            tools = await self.client.list_tools()
            resources = await self.client.list_resources()
            
            return {
                "tools": [
                    {
                        "name": str(tool.name),
                        "description": str(tool.description),
                        "input_schema": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
                    }
                    for tool in tools
                ],
                "resources": [
                    {
                        "uri": str(resource.uri),
                        "name": str(resource.name),
                        "description": str(resource.description) if hasattr(resource, 'description') else ""
                    }
                    for resource in resources
                ]
            }
        except Exception as e:
            logger.error(f"获取MCP能力失败: {e}")
            raise
            
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行指定的工具"""
        try:
            logger.info(f"执行工具 {tool_name}")
            logger.info(f"参数详情: {parameters}")
            
            # 直接使用MermaidMCPClient的render_mermaid方法如果是render_mermaid工具
            if tool_name == "render_mermaid" and hasattr(self.client, 'render_mermaid'):
                script = parameters.get("script", "")
                if not script:
                    raise ValueError("render_mermaid需要'script'参数")
                
                return await self.client.render_mermaid(
                    script=script,
                    format=parameters.get("format", "png"),
                    width=parameters.get("width", 1920),
                    height=parameters.get("height", 1080),
                    background=parameters.get("background", "transparent")
                )
            
            # 使用底层客户端的call_tool方法
            if hasattr(self.client, 'client') and hasattr(self.client.client, 'call_tool'):
                # MermaidMCPClient通过self.client访问底层client
                logger.info(f"调用底层client.call_tool: {tool_name} 参数: {parameters}")
                result = await self.client.client.call_tool(tool_name, parameters)
                return self.client._parse_response_content(result)
            elif hasattr(self.client, 'call_tool'):
                # 直接支持call_tool的客户端
                logger.info(f"调用client.call_tool: {tool_name} 参数: {parameters}")
                return await self.client.call_tool(tool_name, parameters)
            else:
                raise NotImplementedError(f"工具 {tool_name} 的执行方式未实现")
        except Exception as e:
            logger.error(f"执行工具 {tool_name} 失败: {e}")
            logger.error(f"参数详情: {parameters}")
            raise