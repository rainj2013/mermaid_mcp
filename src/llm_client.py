"""
月之暗面(LLM) API客户端
使用OpenAI SDK与Moonshot AI API交互，实现自然语言理解和工具选择
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

当用户询问关于工具、功能或其他问题时，请直接回答。

保持回答简洁、有用、友好。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        if context:
            messages.insert(1, {"role": "system", "content": f"上下文信息: {context}"})
            
        logger.info(f"用户输入: {user_input}")
        if context:
            logger.info(f"上下文信息: {context}")
            
        response = await self.chat_completion(messages, temperature=0.7)
        logger.info(f"大模型回复: {response}")
        return response
    
    async def analyze_tool_intent(
        self, 
        user_input: str, 
        available_tools: List[Dict[str, Any]], 
        available_resources: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        分析用户意图并选择合适的工具
        
        Args:
            user_input: 用户输入文本
            available_tools: 可用的工具详情列表，每个工具包含name, description, input_schema
            available_resources: 可用的资源详情列表，每个资源包含uri, name, description
            
        Returns:
            包含工具选择和意图信息的字典
        """
        tools_json = json.dumps(available_tools, ensure_ascii=False, indent=2) if available_tools else "[]"
        resources_json = json.dumps(available_resources, ensure_ascii=False, indent=2) if available_resources else "[]"
        
        tool_names = [tool['name'] for tool in available_tools] if available_tools else []
        
        system_prompt = (
            "你是一个严格的JSON格式分析器，必须返回有效的JSON格式，不允许返回任何其他格式的文本。\n\n"
            f"当前可用的工具详情：\n{tools_json}\n\n"
            f"当前可用的资源详情：\n{resources_json}\n\n"
            "**任务**：分析用户输入，返回一个严格的JSON对象，格式如下：\n"
            '```json\n'
            '{\n'
            '    "requires_tool": true,\n'
            '    "selected_tool": "具体的工具名称",\n'
            '    "confidence": 0.9,\n'
            '    "reasoning": "选择这个工具的原因",\n'
            '    "direct_response": "",\n'
            '    "tool_parameters": {"参数名": "参数值"},\n'
            '    "tool_description": "工具功能描述"\n'
            '}\n'
            '```\n\n'
            "或者当不需要工具时：\n"
            '```json\n'
            '{\n'
            '    "requires_tool": false,\n'
            '    "selected_tool": "none",\n'
            '    "confidence": 0.0,\n'
            '    "reasoning": "为什么不需要工具",\n'
            '    "direct_response": "直接回复用户的聊天内容",\n'
            '    "tool_parameters": {},\n'
            '    "tool_description": ""\n'
            '}\n'
            '```\n\n'
            "**规则**：\n"
            "1. 必须返回有效的JSON对象\n"
            "2. requires_tool必须是布尔值true/false\n"
            "3. selected_tool必须是字符串，且必须是可用工具列表中的工具名称，或者\"none\"\n"
            "4. confidence必须是0.0到1.0之间的浮点数\n"
            "5. tool_parameters必须根据所选工具的input_schema填写所有必需参数\n"
            "6. 不要返回任何解释性文字，只返回JSON\n"
            "7. 确保JSON格式正确转义所有特殊字符\n\n"
            f"**可用工具列表**：{tool_names}\n\n"
            "请严格按照上述格式返回，不要添加任何额外文字。"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        try:
            content = await self.chat_completion(messages, temperature=0.1)  # 降低温度确保一致性
            logger.info(f"LLM原始响应: {repr(content)}")
            
            # 提取JSON部分 - 使用更健壮的方法
            import re
            
            def extract_and_parse_json(text: str) -> Dict[str, Any]:
                """从文本中提取并解析JSON对象"""
                
                # 方法1：尝试匹配 ```json 块
                json_block_match = re.search(r'```json\s*([\s\S]*?)\s*```', text, re.DOTALL)
                if json_block_match:
                    json_str = json_block_match.group(1).strip()
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        pass
                
                # 方法2：尝试找到完整的JSON对象
                # 使用更智能的JSON对象提取
                brace_count = 0
                start_pos = -1
                json_candidates = []
                
                for i, char in enumerate(text):
                    if char == '{':
                        if brace_count == 0:
                            start_pos = i
                        brace_count += 1
                    elif char == '}' and brace_count > 0:
                        brace_count -= 1
                        if brace_count == 0 and start_pos >= 0:
                            json_str = text[start_pos:i+1]
                            try:
                                parsed = json.loads(json_str)
                                if isinstance(parsed, dict) and "requires_tool" in parsed:
                                    return parsed
                                else:
                                    json_candidates.append(json_str)
                            except json.JSONDecodeError:
                                json_candidates.append(json_str)
                
                # 方法3：尝试修复最后一个候选
                if json_candidates:
                    for json_str in reversed(json_candidates):
                        try:
                            # 修复常见的JSON转义问题
                            fixed_json = json_str
                            # 处理未转义的换行符
                            fixed_json = re.sub(r'(?<!\\)\n', '\\n', fixed_json)
                            # 处理未转义的制表符
                            fixed_json = re.sub(r'(?<!\\)\t', '\\t', fixed_json)
                            # 处理未转义的回车
                            fixed_json = re.sub(r'(?<!\\)\r', '\\r', fixed_json)
                            # 处理引号
                            fixed_json = re.sub(r'(?<!\\)"(?=.*":)', r'\\"', fixed_json)
                            
                            return json.loads(fixed_json)
                        except json.JSONDecodeError:
                            continue
                
                raise json.JSONDecodeError("无法提取有效的JSON", text, 0)
            
            result = extract_and_parse_json(content)
            
            # 验证并修正格式
            tool_name = str(result.get("selected_tool", "none"))
            available_tool_names = [tool['name'] for tool in available_tools] if available_tools else []
            
            if tool_name != "none" and tool_name not in available_tool_names:
                logger.warning(f"选择的工具 {tool_name} 不在可用工具列表中")
                tool_name = "none"
                result["requires_tool"] = False
            
            formatted_result = {
                "requires_tool": bool(result.get("requires_tool", False)),
                "selected_tool": tool_name,
                "confidence": min(1.0, max(0.0, float(result.get("confidence", 0.0)))),
                "reasoning": str(result.get("reasoning", "")),
                "direct_response": str(result.get("direct_response", "")),
                "tool_parameters": dict(result.get("tool_parameters", {})),
                "tool_description": str(result.get("tool_description", ""))
            }
            
            logger.info(f"工具选择分析成功: {json.dumps(formatted_result, ensure_ascii=False, indent=2)}")
            return formatted_result
            
        except Exception as e:
            logger.error(f"分析工具意图失败: {type(e).__name__}: {e}")
            logger.error(f"原始响应: {repr(content)}")
            
            # 如果失败，尝试从响应中提取工具名称和参数
            fallback_response = {
                "requires_tool": False,
                "selected_tool": "none",
                "confidence": 0.0,
                "reasoning": f"解析失败: {str(e)}",
                "direct_response": f"我理解您想要{user_input}，让我为您提供帮助。",
                "tool_parameters": {},
                "tool_description": ""
            }
            
            # 更智能的后备处理
            if any(keyword in user_input.lower() for keyword in ['图', 'chart', 'diagram', '流程', '时序']):
                if available_tools:
                    render_tools = [t for t in available_tools if 'render' in t.get('name', '').lower()]
                    if render_tools and 'script' in str(render_tools[0].get('input_schema', {})):
                        # 尝试生成基本的mermaid脚本
                        basic_script = "graph TD\n    A[开始] --> B[处理中] --> C[结束]"
                        fallback_response.update({
                            "requires_tool": True,
                            "selected_tool": render_tools[0]['name'],
                            "confidence": 0.5,
                            "reasoning": "基于关键词匹配和基础脚本生成",
                            "tool_parameters": {"script": basic_script}
                        })
            
            return fallback_response