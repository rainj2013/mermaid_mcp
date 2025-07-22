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
        "moonshot-v1-128k": "128K上下文长度",
        "kimi-k2-0711-preview":"k2模型，128K上下文长度"
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
    
    async def analyze_tool_intent(
        self, 
        user_input: str, 
        available_tools: List[str], 
        available_resources: List[str] = None
    ) -> Dict[str, Any]:
        """
        分析用户意图并选择合适的工具
        
        Args:
            user_input: 用户输入文本
            available_tools: 可用的工具列表
            available_resources: 可用的资源列表
            
        Returns:
            包含工具选择和意图信息的字典
        """
        tools_str = ", ".join(available_tools) if available_tools else "无可用工具"
        resources_str = ", ".join(available_resources) if available_resources else "无可用资源"
        
        system_prompt = f"""你是一个智能助手，负责分析用户意图并选择合适的工具来满足需求。

当前可用的工具：{tools_str}
当前可用的资源：{resources_str}

请分析用户的输入，判断是否需要使用工具来完成任务：

1. **工具使用判断**：
   - 如果用户需求可以用现有工具解决，选择最合适的工具
   - 如果用户需求不需要工具（如普通聊天、问答、建议等），直接回复
   - 如果没有合适的工具，直接回复用户并说明情况

2. **工具选择标准**：
   - 仔细分析每个工具的功能描述
   - 选择最匹配用户需求的工具
   - 如果多个工具都相关，选择最直接的那个

3. **回复格式**：
请以JSON格式返回分析结果：
{{
    "requires_tool": true/false,
    "selected_tool": "工具名称或"none"",
    "confidence": 0.0-1.0,
    "reasoning": "选择该工具或回复的原因",
    "direct_response": "当requires_tool为false时的直接回复内容",
    "tool_parameters": {{"参数名": "参数值"}}
}}

**示例判断**：
- "帮我画一个流程图" → 如果有mermaid工具，requires_tool=true
- "今天天气怎么样" → 如果没有天气工具，requires_tool=false，直接回复
- "用mermaid画个用户登录流程" → 如果有mermaid工具，requires_tool=true
- "你好" → 普通聊天，requires_tool=false"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        try:
            content = await self.chat_completion(messages, temperature=0.3)
            result = json.loads(content.strip())
            
            # 确保返回格式正确
            return {
                "requires_tool": result.get("requires_tool", False),
                "selected_tool": result.get("selected_tool", "none"),
                "confidence": result.get("confidence", 0.0),
                "reasoning": result.get("reasoning", ""),
                "direct_response": result.get("direct_response", ""),
                "tool_parameters": result.get("tool_parameters", {})
            }
        except json.JSONDecodeError:
            logger.warning("无法解析LLM响应为JSON，使用默认响应")
            return {
                "requires_tool": False,
                "selected_tool": "none",
                "confidence": 0.0,
                "reasoning": "解析失败",
                "direct_response": "我理解您的需求，让我为您提供帮助。",
                "tool_parameters": {}
            }
    
    async def generate_mermaid_script(
        self, 
        user_input: str, 
        chart_type: str = "flowchart",
        examples: Dict[str, str] = None
    ) -> str:
        """
        根据用户输入生成Mermaid脚本
        
        Args:
            user_input: 用户输入文本
            chart_type: 图表类型
            examples: 示例图表字典
            
        Returns:
            Mermaid脚本字符串
        """
        system_prompt = f"""你是一个专业的Mermaid图表生成专家，负责将用户的自然语言描述转换为标准的Mermaid脚本。

请根据用户的描述生成符合Mermaid语法的脚本。必须严格遵守以下语法规范：

**图表类型规范：**
- flowchart: 使用 `graph TD` (从上到下) 或 `graph LR` (从左到右)
- sequence: 使用 `sequenceDiagram`
- class: 使用 `classDiagram`
- state: 使用 `stateDiagram-v2`
- entity: 使用 `erDiagram` (实体关系图)
- journey: 使用 `journey`
- gantt: 使用 `gantt`

**通用语法规则：**
1. 图表必须以大写图表类型声明开始，如 `graph TD`
2. 节点ID只能包含字母、数字和下划线，不能包含空格或特殊字符
3. 节点标签用方括号 `[标签]` 或圆括号 `(标签)`
4. 连接线使用 `-->` (实线箭头) 或 `---` (实线无箭头)
5. 子图使用 `subgraph 标题...end`
6. 避免使用中文或特殊字符作为节点ID

**具体语法示例：**
- flowchart: A[开始] --> B{{判断条件}} -->|是| C[处理]
- sequence: participant Alice; Alice->>Bob: 消息
- class: class Animal {{{{+String name +int age +makeSound()}}}}
- state: state 状态名 {{{{ 状态描述 }}}}
- entity: entity 实体名 {{{{ 属性名 类型 }}}}
- journey: 标题: 任务: 分数: 参与者
- gantt: dateFormat YYYY-MM-DD; section 任务

**错误避免：**
- 不要使用空格或特殊字符作为节点ID
- 确保所有箭头连接都是有效的
- 不要混用不同图表类型的语法
- 确保括号匹配

使用图表类型：{chart_type}

参考示例：
{json.dumps(examples, ensure_ascii=False, indent=2)}

请直接返回Mermaid脚本，不要包含额外的解释或标记，确保语法100%正确。"""

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