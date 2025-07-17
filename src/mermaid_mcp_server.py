from fastmcp import FastMCP
import os
import tempfile
import hashlib
import subprocess
from typing import Dict, Any
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, filename='mermaid_mcp.log', filemode='a', format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# 创建 MCP 服务器
mcp = FastMCP("mermaid绘图助手")

# 全局配置
SYSTEM_MERMAID_CLI = "mmdc.cmd" if os.name == "nt" else "mmdc"
MERMAID_CLI_PATH = os.environ.get("MERMAID_CLI_PATH", SYSTEM_MERMAID_CLI)
OUTPUT_DIR = os.environ.get("MERMAID_OUTPUT_DIR", "./output")
IMAGE_FORMAT = os.environ.get("MERMAID_IMAGE_FORMAT", "png")

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _generate_file_id(script: str) -> str:
    """根据脚本内容生成唯一文件ID"""
    return hashlib.md5(script.encode()).hexdigest()[:12]


def _check_mermaid_cli() -> bool:
    """检查mermaid cli是否可用"""
    try:
        subprocess.run([MERMAID_CLI_PATH, "--version"], 
                      capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _install_mermaid_cli():
    """安装mermaid cli"""
    try:
        subprocess.run(["npm", "install", "-g", "@mermaid-js/mermaid-cli"], 
                      check=True)
        logger.info("Mermaid CLI installed successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install Mermaid CLI: {e}")
        raise RuntimeError("Mermaid CLI installation failed")


@mcp.tool(
    name="render_mermaid",
    description="""
    渲染Mermaid脚本为图片，返回图片的本地路径。
    
    参数：
        script: Mermaid脚本内容
        format: 输出格式，支持png、svg、pdf（默认png）
        width: 图片宽度（默认800）
        height: 图片高度（默认600）
        background: 背景颜色（默认transparent）
    
    返回：
        dict: 包含success、image_path、file_id的字典
    """
)
def render_mermaid(
    script: str, 
    format: str = "png", 
    width: int = 800, 
    height: int = 600, 
    background: str = "transparent"
) -> Dict[str, Any]:
    """
    渲染Mermaid脚本为图片
    """
    try:
        # 检查Mermaid CLI
        if not _check_mermaid_cli():
            logger.warning("Mermaid CLI not found, attempting to install...")
            _install_mermaid_cli()
            if not _check_mermaid_cli():
                return {
                    "success": False,
                    "error": "Mermaid CLI (mmdc) not available. Please install with: npm install -g @mermaid-js/mermaid-cli"
                }
        
        # 生成文件ID和输出路径
        file_id = _generate_file_id(script)
        output_filename = f"mermaid_{file_id}.{format}"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        # 创建临时文件存储mermaid脚本
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as temp_file:
            temp_file.write(script)
            temp_mermaid_path = temp_file.name
        
        try:
            # 构建mermaid-cli命令
            cmd = [
                MERMAID_CLI_PATH,
                "--input", temp_mermaid_path,
                "--output", output_path,
                "--outputFormat", format,
                "--width", str(width),
                "--height", str(height),
                "--backgroundColor", background,
                "--puppeteerConfigFile", "puppeteer-config.json"
            ]
            
            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Mermaid CLI error: {result.stderr}")
                return {
                    "success": False,
                    "error": f"Failed to generate diagram: {result.stderr}"
                }
            
            # 记录成功时的输出
            if result.stdout:
                logger.info(f"Mermaid CLI stdout: {result.stdout}")
            
            # 检查文件是否生成成功
            if not os.path.exists(output_path):
                return {
                    "success": False,
                    "error": "Output file was not created"
                }
            
            # 获取文件大小
            file_size = os.path.getsize(output_path)
            
            logger.info(f"Successfully generated diagram: {output_path} ({file_size} bytes)")
            
            return {
                "success": True,
                "image_path": output_path,
                "file_id": file_id,
                "format": format,
                "size": file_size,
                "stdout": result.stdout.strip() if result.stdout else "",
                "stderr": result.stderr.strip() if result.stderr else ""
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Mermaid rendering timed out (30s limit)"
            }
        except Exception as e:
            logger.error(f"Unexpected error during rendering: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
        finally:
            # 清理临时文件
            if os.path.exists(temp_mermaid_path):
                os.unlink(temp_mermaid_path)
                
    except Exception as e:
        logger.error(f"Error in render_mermaid: {e}")
        return {
            "success": False,
            "error": f"Internal error: {str(e)}"
        }


@mcp.tool(
    name="validate_mermaid",
    description="""
    验证Mermaid脚本的语法是否正确。
    
    参数：
        script: Mermaid脚本内容
    
    返回：
        dict: 包含is_valid和错误信息的字典
    """
)
def validate_mermaid(script: str) -> Dict[str, Any]:
    """
    验证Mermaid脚本的语法
    """
    try:
        # 创建临时文件进行验证
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as temp_file:
            temp_file.write(script)
            temp_mermaid_path = temp_file.name
        
        try:
            # 使用mermaid-cli的验证模式
            cmd = [
                MERMAID_CLI_PATH,
                "--input", temp_mermaid_path,
                "--output", "/dev/null",  # 不实际生成文件
                "--quiet",
                "--puppeteerConfigFile", os.path.join(os.path.dirname(__file__), "puppeteer-config.json")
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            is_valid = result.returncode == 0
            
            return {
                "is_valid": is_valid,
                "error": result.stderr if not is_valid else None
            }
            
        except subprocess.TimeoutExpired:
            return {
                "is_valid": False,
                "error": "Validation timed out"
            }
        finally:
            if os.path.exists(temp_mermaid_path):
                os.unlink(temp_mermaid_path)
                
    except Exception as e:
        return {
            "is_valid": False,
            "error": f"Validation error: {str(e)}"
        }


@mcp.tool(
    name="get_supported_formats",
    description="获取支持的输出格式列表"
)
def get_supported_formats() -> Dict[str, Any]:
    """
    获取支持的输出格式
    """
    return {
        "formats": ["png", "svg", "pdf"],
        "default": "png",
        "descriptions": {
            "png": "Portable Network Graphics - 位图格式，适合网页使用",
            "svg": "Scalable Vector Graphics - 矢量格式，可无损缩放",
            "pdf": "Portable Document Format - 适合打印和高保真文档"
        }
    }


@mcp.resource("config://output_directory")
def get_output_directory() -> str:
    """获取当前输出目录路径"""
    return OUTPUT_DIR


@mcp.resource("config://cli_path")
def get_cli_path() -> str:
    """获取当前mermaid-cli路径"""
    return MERMAID_CLI_PATH


@mcp.resource("examples://flowchart")
def get_flowchart_example() -> str:
    """获取流程图示例"""
    return """
    ```mermaid
    flowchart TD
        A[开始] --> B{条件判断}
        B -->|是| C[执行操作1]
        B -->|否| D[执行操作2]
        C --> E[结束]
        D --> E
    ```
    """


@mcp.resource("examples://sequence")
def get_sequence_example() -> str:
    """获取时序图示例"""
    return """
    ```mermaid
    sequenceDiagram
        participant A as 用户
        participant B as 系统
        participant C as 数据库
        
        A->>B: 登录请求
        B->>C: 验证用户
        C-->>B: 验证结果
        B-->>A: 登录响应
    ```
    """


if __name__ == "__main__":
    # 运行MCP服务器
    mcp.run(transport='sse', port=8000)