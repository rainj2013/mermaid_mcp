"""
月之暗面(LLM) API客户端
使用OpenAI SDK与Moonshot AI API交互，实现自然语言理解和Mermaid脚本生成
基于Moonshot官方API文档: https://platform.moonshot.cn/docs/api/chat
"""

import json
import logging
from typing import Dict, Any, List
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class MoonshotClient:
    """月之暗面API客户端 - 使用OpenAI SDK实现"""
    
    # 支持的模型列表
    SUPPORTED_MODELS = {
        "moonshot-v1-8k": "8K上下文长度",
        "moonshot-v1-32k": "32K上下文长度", 
        "moonshot-v1-128k": "128K上下文长度"
    }
    
    def __init__(self, api_key: str, base_url: str = "https://api.moonshot.cn/v1", model: str = "moonshot-v1-8k"):
        """
        初始化月之暗面API客户端
        
        Args:
            api_key: API密钥 (从 https://platform.moonshot.cn 获取)
            base_url: API基础URL，默认为 https://api.moonshot.cn/v1
            model: 使用的模型名称，可选值：moonshot-v1-8k, moonshot-v1-32k, moonshot-v1-128k
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        
        # 验证模型名称
        if model not in self.SUPPORTED_MODELS:
            logger.warning(f"模型 {model} 不在支持的模型列表中，使用默认模型 moonshot-v1-8k")
            self.model = "moonshot-v1-8k"
        else:
            self.model = model
            
        # 使用OpenAI SDK初始化客户端
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=self.base_url,
            timeout=30.0
        )
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.client.close()
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        temperature: float = 0.7,
        max_tokens: int = 2000,
        top_p: float = 1.0,
        **kwargs
    ) -> str:
        """
        发送聊天完成请求 - 使用OpenAI SDK
        
        Args:
            messages: 消息列表，格式：[{"role": "system"|"user"|"assistant", "content": "..."}]
            temperature: 温度参数，控制随机性，范围 0.0-2.0，默认 0.7
            max_tokens: 最大生成token数，范围 1-8192，默认 2000
            top_p: 核采样参数，范围 0.0-1.0，默认 1.0
            **kwargs: 其他OpenAI API参数
            
        Returns:
            生成的内容字符串
        """
        try:
            # 使用OpenAI SDK调用月之暗面API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=max(0.0, min(2.0, temperature)),  # 确保在有效范围内
                max_tokens=max(1, min(8192, max_tokens)),      # 确保在有效范围内
                top_p=max(0.0, min(1.0, top_p)),              # 确保在有效范围内
                **kwargs
            )
            
            # 提取生成的内容
            if response.choices and response.choices[0].message:
                return response.choices[0].message.content or ""
            else:
                return ""
                
        except Exception as e:
            logger.error(f"OpenAI SDK调用失败: {e}")
            raise Exception(f"月之暗面API调用失败: {e}")
    
    async def chat_with_user(self, user_input: str, context: str = "") -> str:
        """
        与用户进行通用聊天
        
        Args:
            user_input: 用户输入文本
            context: 可选的上下文信息
            
        Returns:
            LLM的回复内容
        """
        system_prompt = """你是一个智能助手，可以回答各种问题，提供建议，帮助用户解决各种问题。

当用户询问关于图表、流程图、时序图、类图等可视化内容时，你可能会建议使用Mermaid工具。
当用户询问其他问题时，请直接回答。

保持回答简洁、有用、友好。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        if context:
            messages.insert(1, {"role": "system", "content": f"上下文信息: {context}"})
            
        return await self.chat_completion(messages, temperature=0.7)
    
    async def detect_mermaid_intent(self, user_input: str) -> Dict[str, Any]:
        """
        检测用户输入是否包含Mermaid绘图意图
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            包含意图信息的字典
        """
        system_prompt = """你是一个意图分析专家，负责分析用户输入是否需要绘制Mermaid图表。

请分析用户输入，判断以下信息：
1. 是否需要绘制Mermaid图表
2. 图表类型（flowchart, sequence, class, state, entity, user-journey, gantt等）
3. 如果不需要绘图，直接回复用户的内容

请以JSON格式返回分析结果：
{
    "has_intent": true/false,
    "confidence": 0.0-1.0,
    "chart_type": "图表类型",
    "direct_response": "当has_intent为false时的直接回复内容"
}

当用户只是普通聊天或询问非图表相关问题时，has_intent为false，direct_response包含适当的回复。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        try:
            content = await self.chat_completion(messages, temperature=0.3)
            return json.loads(content.strip())
        except json.JSONDecodeError:
            logger.warning("无法解析LLM响应为JSON，使用默认响应")
            return {
                "has_intent": False,
                "confidence": 0.0,
                "chart_type": "",
                "direct_response": "我理解您的需求，让我为您提供帮助。"
            }
    
    async def generate_mermaid_script(
        self, 
        user_input: str, 
        chart_type: str,
        mcp_tools: List[str], 
        mcp_resources: List[str],
        examples: Dict[str, str]
    ) -> str:
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
        
        content = await self.chat_completion(messages, temperature=0.5)
        
        # 清理响应内容，移除可能的markdown标记
        script = content.strip()
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
        
        content = await self.chat_completion(messages, temperature=0.5)
        
        # 清理响应内容
        script = content.strip()
        if script.startswith("```mermaid"):
            script = script[10:]
        if script.startswith("```"):
            script = script[3:]
        if script.endswith("```"):
            script = script[:-3]
            
        return script.strip()