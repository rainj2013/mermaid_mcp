"""
月之暗面(LLM) API客户端
用于与Moonshot AI API交互，实现自然语言理解和Mermaid脚本生成
"""

import json
import logging
from typing import Dict, Any, Optional, List
import aiohttp
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class LLMResponse:
    """LLM响应数据结构"""
    content: str
    usage: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None

class MoonshotClient:
    """月之暗面API客户端"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.moonshot.cn/v1", model: str = "moonshot-v1-8k"):
        """
        初始化月之暗面API客户端
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            model: 使用的模型名称
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.session = None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            headers={
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            },
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()
            
    async def chat_completion(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> LLMResponse:
        """
        发送聊天完成请求
        
        Args:
            messages: 消息列表，格式：[{"role": "user", "content": "..."}]
            temperature: 温度参数，控制随机性
            
        Returns:
            LLMResponse对象
        """
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
            
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 2000
        }
        
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API错误 {response.status}: {error_text}")
                    
                data = await response.json()
                
                if "choices" not in data or not data["choices"]:
                    raise Exception("API响应格式错误")
                    
                choice = data["choices"][0]
                content = choice.get("message", {}).get("content", "")
                
                return LLMResponse(
                    content=content,
                    usage=data.get("usage"),
                    finish_reason=choice.get("finish_reason")
                )
                
        except aiohttp.ClientError as e:
            logger.error(f"网络请求失败: {e}")
            raise
        except Exception as e:
            logger.error(f"API调用失败: {e}")
            raise
            
    async def detect_mermaid_intent(self, user_input: str) -> Dict[str, Any]:
        """
        检测用户输入是否包含Mermaid绘图意图
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            包含意图信息的字典
        """
        system_prompt = """你是一个专业的Mermaid图表专家，负责分析用户输入并判断其是否需要绘制Mermaid图表。

请分析用户输入，判断以下信息：
1. 是否需要绘制Mermaid图表
2. 图表类型（flowchart, sequence, class, state, entity, user-journey, gantt等）
3. 图表的主题和目的
4. 关键元素和关系

请以JSON格式返回分析结果：
{
    "has_intent": true/false,
    "confidence": 0.0-1.0,
    "chart_type": "图表类型",
    "description": "图表描述",
    "elements": ["元素列表"],
    "relationships": ["关系列表"]
}

如果不需要绘制图表，has_intent为false，其他字段可以为空。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        response = await self.chat_completion(messages, temperature=0.3)
        
        try:
            return json.loads(response.content.strip())
        except json.JSONDecodeError:
            logger.warning("无法解析LLM响应为JSON，使用默认响应")
            return {
                "has_intent": False,
                "confidence": 0.0,
                "chart_type": "",
                "description": "",
                "elements": [],
                "relationships": []
            }
            
    async def generate_mermaid_script(self, user_input: str, chart_type: str, 
                                    mcp_tools: List[str], mcp_resources: List[str],
                                    examples: Dict[str, str]) -> str:
        """
        根据用户输入生成Mermaid脚本
        
        Args:
            user_input: 用户输入文本
            chart_type: 图表类型
            mcp_tools: 可用的MCP工具列表
            mcp_resources: 可用的MCP资源列表
            examples: 示例图表字典
            
        Returns:
            Mermaid脚本字符串
        """
        system_prompt = f"""你是一个专业的Mermaid图表生成专家，负责将用户的自然语言描述转换为标准的Mermaid脚本。

请根据用户的描述生成符合Mermaid语法的脚本。注意以下要求：

1. 使用标准的Mermaid语法
2. 图表要清晰、简洁、美观
3. 节点命名要有意义
4. 连线要清晰表示关系
5. 使用合适的图表类型：{chart_type}

可用工具：{', '.join(mcp_tools)}
可用资源：{', '.join(mcp_resources)}

参考示例：
{json.dumps(examples, ensure_ascii=False, indent=2)}

请直接返回Mermaid脚本，不要包含额外的解释或标记。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请根据以下描述生成{chart_type}图表：{user_input}"}
        ]
        
        response = await self.chat_completion(messages, temperature=0.5)
        
        # 清理响应内容，移除可能的markdown标记
        script = response.content.strip()
        if script.startswith("```mermaid"):
            script = script[10:]
        if script.startswith("```"):
            script = script[3:]
        if script.endswith("```"):
            script = script[:-3]
            
        return script.strip()
        
    async def improve_mermaid_script(self, current_script: str, feedback: str) -> str:
        """
        根据用户反馈改进现有的Mermaid脚本
        
        Args:
            current_script: 当前的Mermaid脚本
            feedback: 用户反馈
            
        Returns:
            改进后的Mermaid脚本
        """
        system_prompt = """你是一个Mermaid图表优化专家，负责根据用户反馈改进现有的Mermaid脚本。

请根据用户反馈对现有脚本进行改进，保持语法的正确性，同时满足用户的需求。
请直接返回改进后的Mermaid脚本，不要包含额外的解释。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"现有脚本：\n{current_script}\n\n用户反馈：{feedback}"}
        ]
        
        response = await self.chat_completion(messages, temperature=0.5)
        
        # 清理响应内容
        script = response.content.strip()
        if script.startswith("```mermaid"):
            script = script[10:]
        if script.startswith("```"):
            script = script[3:]
        if script.endswith("```"):
            script = script[:-3]
            
        return script.strip()