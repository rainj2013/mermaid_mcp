#!/usr/bin/env python3
"""
MCP Client for Mermaid MCP Server
This client connects to the mermaid_mcp_server and provides a simple interface to render mermaid diagrams.
"""

import asyncio
import json
import logging
from typing import Dict, Any
from fastmcp import Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('mcp_client.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class MermaidMCPClient:
    """Client for interacting with the Mermaid MCP Server"""
    
    def __init__(self, server_url: str = "http://127.0.0.1:8000/sse", command: list = None):
        """
        Initialize the Mermaid MCP Client
        
        Args:
            server_url: URL for the MCP server (default: http://127.0.0.1:8000/sse)
            command: Command for stdio transport (if using stdio)
        """
        self.server_url = server_url
        self.command = command
        self.client = None
        logger.info(f"Initialized MermaidMCPClient with server_url: {server_url}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        try:
            if self.command:
                # stdio transport
                logger.info(f"Connecting via stdio with command: {' '.join(self.command)}")
                self.client = Client(self.command)
            else:
                # HTTP/SSE transport
                logger.info(f"Connecting via HTTP/SSE to: {self.server_url}")
                self.client = Client(self.server_url)
            
            await self.client.__aenter__()
            logger.info("Successfully connected to MCP server")
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
    
    async def list_tools(self) -> list:
        """List all available tools from the server"""
        logger.debug("Listing available tools")
        tools = await self.client.list_tools()
        logger.info(f"Found {len(tools)} tools")
        return tools
    
    async def list_resources(self) -> list:
        """List all available resources from the server"""
        logger.debug("Listing available resources")
        resources = await self.client.list_resources()
        logger.info(f"Found {len(resources)} resources")
        return resources
    
    async def render_mermaid(
        self, 
        script: str, 
        format: str = "png", 
        width: int = 800, 
        height: int = 600, 
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
        
        # Parse response like working demo
        if hasattr(result, 'content') and result.content:
            content_text = result.content[0].text
            return json.loads(content_text)
        return {"success": False, "error": "No content"}
    
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
        
        result = await self.client.call_tool(
            "validate_mermaid",
            {"script": script}
        )
        
        # Parse response like working demo
        if hasattr(result, 'content') and result.content:
            content_text = result.content[0].text
            return json.loads(content_text)
        return {"is_valid": False, "error": "No content"}
    
    async def get_supported_formats(self) -> Dict[str, Any]:
        """Get list of supported output formats"""
        logger.info("Getting supported formats")
        
        result = await self.client.call_tool("get_supported_formats", {})
        
        # Parse response like working demo
        if hasattr(result, 'content') and result.content:
            content_text = result.content[0].text
            return json.loads(content_text)
        return {"formats": [], "error": "No content"}
    
    async def get_output_directory(self) -> str:
        """Get current output directory from server"""
        logger.debug("Getting output directory")
        try:
            result = await self.client.read_resource("config://output_directory")
            if result and result[0].content:
                directory = result[0].content
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
            result = await self.client.read_resource("config://cli_path")
            if result and result[0].content:
                cli_path = result[0].content
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
            flowchart = await self.client.read_resource("examples://flowchart")
            if flowchart and flowchart[0].content:
                examples["flowchart"] = flowchart[0].content
            else:
                examples["flowchart"] = "graph TD\n    A[Start] --> B[Process]\n    B --> C[End]"
        except:
            examples["flowchart"] = "graph TD\n    A[Start] --> B[Process]\n    B --> C[End]"
        
        try:
            sequence = await self.client.read_resource("examples://sequence")
            if sequence and sequence[0].content:
                examples["sequence"] = sequence[0].content
            else:
                examples["sequence"] = "sequenceDiagram\n    Alice->>Bob: Hello\n    Bob-->>Alice: Hi there!"
        except:
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
                            print(f"  • {tool.name}: {tool.description}")
                        logger.info(f"Displayed {len(tools)} tools")
                            
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
                            if "error" not in result:
                                print(f"  Valid: {result.get('is_valid', False)}")
                                if result.get('error'):
                                    print(f"  Error: {result.get('error')}")
                            else:
                                print(f"  Error: {result.get('error', 'Unknown error')}")
                            logger.info("Completed validation")
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