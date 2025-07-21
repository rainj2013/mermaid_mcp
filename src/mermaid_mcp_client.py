#!/usr/bin/env python3
"""
MCP Client for Mermaid MCP Server
This client connects to the mermaid_mcp_server and provides a simple interface to render mermaid diagrams.
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from fastmcp import Client

# Configure logging to use project root/logs directory
project_root = Path(__file__).parent.parent
log_dir = project_root / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "mcp_client.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class MermaidMCPClient:
    """Client for interacting with the Mermaid MCP Server"""
    
    def __init__(self, server_url: str = "http://127.0.0.1:8000/sse"):
        """
        Initialize the Mermaid MCP Client
        
        Args:
            server_url: URL for the MCP server (default: http://127.0.0.1:8000/sse)
            command: Command for stdio transport (if using stdio)
        """
        self.server_url = server_url
        self.client: Optional[Client] = None
        logger.info(f"Initialized MermaidMCPClient with server_url: {server_url}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        try:
            # HTTP/SSE transport
            logger.info(f"Connecting via HTTP/SSE to: {self.server_url}")
            self.client = Client(self.server_url)
            
            await self.client.__aenter__()
            logger.info("Successfully connected to MCP server")
            
            # 启动时执行list_tools和list_resources
            logger.info("🔍 正在获取服务器信息...")
            try:
                tools = await self.list_tools()
                logger.info(f"✅ 发现 {len(tools)} 个可用工具")
                
                resources = await self.list_resources()
                logger.info(f"✅ 发现 {len(resources)} 个可用资源")
                
                # 打印工具详情
                if tools:
                    logger.info("📋 可用工具列表:")
                    for tool in tools:
                        logger.info(f"  • {tool.name}: {tool.description}")
                
                # 打印资源详情
                if resources:
                    logger.info("📁 可用资源列表:")
                    for resource in resources:
                        logger.info(f"  • {resource.uri}: {resource.name}")
                        
            except Exception as e:
                logger.warning(f"获取服务器信息时出现警告: {e}")
                logger.info("继续运行，但某些功能可能不可用")
            
            return self
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            logger.error("💡 Make sure the server is running: python src/mermaid_mcp_server.py")
            logger.error("💡 Check if server is listening on http://127.0.0.1:8000/sse")
            raise
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            try:
                await self.client.__aexit__(exc_type, exc_val, exc_tb)
                logger.info("Disconnected from MCP server")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
                raise
    
    def _check_client(self) -> None:
        """Check if client is initialized"""
        if self.client is None:
            raise RuntimeError("Client is not initialized. Make sure to use async context manager.")
    
    async def list_tools(self) -> List[Any]:
        """List all available tools from the server"""
        logger.debug("Listing available tools")
        self._check_client()
        assert self.client is not None  # Type checker hint
        tools = await self.client.list_tools()
        logger.info(f"Found {len(tools)} tools")
        return tools
    
    async def list_resources(self) -> List[Any]:
        """List all available resources from the server"""
        logger.debug("Listing available resources")
        self._check_client()
        assert self.client is not None  # Type checker hint
        resources = await self.client.list_resources()
        logger.info(f"Found {len(resources)} resources")
        return resources
    
    def _parse_response_content(self, result: Any) -> Dict[str, Any]:
        """Parse response content safely"""
        try:
            if hasattr(result, 'content') and result.content:
                # Try to get text content from the first content item
                first_content = result.content[0]
                if hasattr(first_content, 'text'):
                    content_text = first_content.text
                    return json.loads(content_text)
                elif hasattr(first_content, 'data'):
                    # Handle binary content
                    return {"success": True, "data": first_content.data}
                else:
                    # Try to convert to string
                    content_text = str(first_content)
                    return json.loads(content_text)
            return {"success": False, "error": "No content"}
        except (json.JSONDecodeError, AttributeError, IndexError) as e:
            logger.error(f"Error parsing response content: {e}")
            return {"success": False, "error": f"Failed to parse response: {e}"}
    
    async def render_mermaid(
        self, 
        script: str, 
        format: str = "png", 
        width: int = 1920, 
        height: int = 1080, 
        background: str = "transparent"
    ) -> Dict[str, Any]:
        """
        Render a mermaid diagram
        
        Args:
            script: Mermaid script content
            format: Output format (png, svg, pdf)
            width: Image width
            height: Image height
            background: Background color
            
        Returns:
            Dict containing success status, image path, and other metadata
        """
        logger.info(f"Rendering mermaid diagram with format: {format}")
        logger.debug(f"Script: {script}")
        
        self._check_client()
        assert self.client is not None  # Type checker hint
        result = await self.client.call_tool(
            "render_mermaid",
            {
                "script": script,
                "format": format,
                "width": width,
                "height": height,
                "background": background
            }
        )
        
        return self._parse_response_content(result)
    
    async def validate_mermaid(self, script: str) -> Dict[str, Any]:
        """
        Validate mermaid script syntax
        
        Args:
            script: Mermaid script content
            
        Returns:
            Dict containing validation result
        """
        logger.info("Validating mermaid script")
        logger.debug(f"Script: {script}")
        
        self._check_client()
        assert self.client is not None  # Type checker hint
        result = await self.client.call_tool(
            "validate_mermaid",
            {"script": script}
        )
        
        return self._parse_response_content(result)
    
    async def get_supported_formats(self) -> Dict[str, Any]:
        """Get list of supported output formats"""
        logger.info("Getting supported formats")
        
        self._check_client()
        assert self.client is not None  # Type checker hint
        result = await self.client.call_tool("get_supported_formats", {})
        
        return self._parse_response_content(result)
    
    def _parse_resource_content(self, result: List[Any]) -> Optional[str]:
        """Parse resource content safely"""
        try:
            if result and len(result) > 0:
                first_result = result[0]
                if hasattr(first_result, 'content'):
                    return first_result.content
                elif hasattr(first_result, 'data'):
                    return first_result.data.decode('utf-8') if isinstance(first_result.data, bytes) else str(first_result.data)
            return None
        except (AttributeError, IndexError, UnicodeDecodeError) as e:
            logger.error(f"Error parsing resource content: {e}")
            return None
    
    async def get_output_directory(self) -> str:
        """Get current output directory from server"""
        logger.debug("Getting output directory")
        try:
            self._check_client()
            assert self.client is not None  # Type checker hint
            result = await self.client.read_resource("config://output_directory")
            directory = self._parse_resource_content(result)
            if directory:
                logger.info(f"Output directory: {directory}")
                return directory
            return "./output"
        except Exception as e:
            logger.error(f"Error getting output directory: {e}")
            return "./output"
    
    async def get_cli_path(self) -> str:
        """Get current mermaid-cli path from server"""
        logger.debug("Getting CLI path")
        try:
            self._check_client()
            assert self.client is not None  # Type checker hint
            result = await self.client.read_resource("config://cli_path")
            cli_path = self._parse_resource_content(result)
            if cli_path:
                logger.info(f"CLI path: {cli_path}")
                return cli_path
            return "mmdc"
        except Exception as e:
            logger.error(f"Error getting CLI path: {e}")
            return "mmdc"
    
    async def get_examples(self) -> Dict[str, str]:
        """Get example mermaid scripts"""
        logger.debug("Getting examples")
        examples = {}
        
        try:
            self._check_client()
            assert self.client is not None  # Type checker hint
            flowchart = await self.client.read_resource("examples://flowchart")
            flowchart_content = self._parse_resource_content(flowchart)
            if flowchart_content:
                examples["flowchart"] = flowchart_content
            else:
                examples["flowchart"] = "graph TD\n    A[Start] --> B[Process]\n    B --> C[End]"
        except Exception as e:
            logger.warning(f"Error getting flowchart example: {e}")
            examples["flowchart"] = "graph TD\n    A[Start] --> B[Process]\n    B --> C[End]"
        
        try:
            assert self.client is not None  # Type checker hint
            sequence = await self.client.read_resource("examples://sequence")
            sequence_content = self._parse_resource_content(sequence)
            if sequence_content:
                examples["sequence"] = sequence_content
            else:
                examples["sequence"] = "sequenceDiagram\n    Alice->>Bob: Hello\n    Bob-->>Alice: Hi there!"
        except Exception as e:
            logger.warning(f"Error getting sequence example: {e}")
            examples["sequence"] = "sequenceDiagram\n    Alice->>Bob: Hello\n    Bob-->>Alice: Hi there!"
        
        return examples


def get_multiline_input(prompt: str) -> str:
    """Get multi-line input from user"""
    print(prompt)
    lines = []
    while True:
        line = input()
        if line == "" and lines and lines[-1] == "":
            # Remove the last empty line and finish
            lines.pop()
            break
        lines.append(line)
    return "\n".join(lines)


async def interactive_mode():
    """Interactive mode for keyboard input with logging"""
    logger.info("Starting interactive mode")
    print("🎮 Mermaid MCP Client Interactive Mode")
    print("=" * 50)
    print("💡 Ensure the Mermaid MCP Server is running on http://127.0.0.1:8000")
    print("   Start server with: python src/mermaid_mcp_server.py")
    print("=" * 50)
    print("Commands:")
    print("  render   - Render a mermaid diagram")
    print("  validate - Validate mermaid syntax")
    print("  formats  - List supported formats")
    print("  examples - Show example diagrams")
    print("  tools    - List available tools")
    print("  resources - List available resources")
    print("  quit     - Exit the program")
    print()
    
    try:
        async with MermaidMCPClient() as client:
            while True:
                try:
                    command = input("\n> ").strip().lower()
                    
                    if command in ["quit", "exit", "q"]:
                        logger.info("User requested exit")
                        print("👋 Goodbye!")
                        break
                        
                    elif command == "tools":
                        logger.info("User requested tools list")
                        tools = await client.list_tools()
                        print("\n📋 Available Tools:")
                        for tool in tools:
                            print(f"  • {str(tool.name)}: {str(tool.description)}")
                        logger.info(f"Displayed {len(tools)} tools")
                            
                    elif command == "resources":
                        logger.info("User requested resources list")
                        resources = await client.list_resources()
                        print("\n📁 Available Resources:")
                        for resource in resources:
                            print(f"  • {str(resource.uri)}: {str(resource.name)}")
                        logger.info(f"Displayed {len(resources)} resources")
                            
                    elif command == "formats":
                        logger.info("User requested formats")
                        formats = await client.get_supported_formats()
                        print("\n🎨 Supported Formats:")
                        if "error" not in formats:
                            for fmt, desc in formats.get("descriptions", {}).items():
                                print(f"  • {fmt}: {desc}")
                            print(f"  Default: {formats.get('default', 'png')}")
                        else:
                            print(f"  Error: {formats.get('error')}")
                        logger.info("Displayed supported formats")
                            
                    elif command == "examples":
                        logger.info("User requested examples")
                        examples = await client.get_examples()
                        print("\n📖 Examples:")
                        for name, example in examples.items():
                            print(f"\n{name.upper()}:")
                            print(example)
                        logger.info("Displayed examples")
                            
                    elif command == "validate":
                        logger.info("User requested validation")
                        script = get_multiline_input("Enter mermaid script to validate (press Enter twice to finish):")
                        
                        if script.strip():
                            result = await client.validate_mermaid(script)
                            print(f"\nValidation Result:")
                            if result.get('is_valid', False):
                                print("✅ 解析成功")
                                logger.info("Mermaid script validation successful")
                            else:
                                error_msg = result.get('error', '未知错误')
                                print(f"❌ 解析失败: {error_msg}")
                                logger.error(f"Mermaid script validation failed: {error_msg}")
                        else:
                            print("❌ No script provided")
                            
                    elif command == "render":
                        logger.info("User requested rendering")
                        script = get_multiline_input("Enter mermaid script to render (press Enter twice to finish):")
                        
                        if script.strip():
                            format_choice = input("Format (png/svg/pdf) [png]: ").strip().lower() or "png"
                            
                            logger.info(f"Rendering with format: {format_choice}")
                            print("🔄 Rendering...")
                            result = await client.render_mermaid(script, format=format_choice)
                            
                            if "error" not in result:
                                if result.get("success"):
                                    print(f"✅ Success!")
                                    print(f"📁 File: {result.get('image_path')}")
                                    print(f"📊 Size: {result.get('size', 0)} bytes")
                                    print(f"🆔 ID: {result.get('file_id')}")
                                    logger.info(f"Successfully rendered: {result.get('image_path')}")
                                else:
                                    print(f"❌ Error: {result.get('error')}")
                                    logger.error(f"Rendering failed: {result.get('error')}")
                            else:
                                print(f"❌ Error: {result.get('error')}")
                                logger.error(f"Rendering failed: {result.get('error')}")
                        else:
                            print("❌ No script provided")
                            
                    elif command == "help":
                        logger.info("User requested help")
                        print("\n📖 Available commands:")
                        print("  render   - Render a mermaid diagram")
                        print("  validate - Validate mermaid syntax") 
                        print("  formats  - List supported formats")
                        print("  examples - Show example diagrams")
                        print("  tools    - List available tools")
                        print("  resources - List available resources")
                        print("  quit     - Exit the program")
                        
                    elif command == "":
                        continue
                        
                    else:
                        logger.warning(f"Unknown command: {command}")
                        print(f"❓ Unknown command: {command}")
                        print("Type 'help' for available commands")
                        
                except KeyboardInterrupt:
                    logger.info("User interrupted with Ctrl+C")
                    print("\n👋 Goodbye!")
                    break
                except Exception as e:
                    logger.error(f"Error in interactive mode: {e}")
                    print(f"❌ Error: {e}")
                    print("Make sure the server is running: python src/mermaid_mcp_server.py")
                    
    except Exception as e:
        logger.error(f"Failed to start interactive mode: {e}")
        print(f"❌ Failed to connect: {e}")
        print("💡 Troubleshooting:")
        print("   1. Start the server: python src/mermaid_mcp_server.py")
        print("   2. Check if server is running: curl http://127.0.0.1:8000/sse")
        print("   3. Verify firewall settings allow connections to port 8000")


if __name__ == "__main__":
    asyncio.run(interactive_mode())