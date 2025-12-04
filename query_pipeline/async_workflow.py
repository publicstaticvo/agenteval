"""
workflow.py - 科研查询优化工作流（工具感知版）

LangGraph workflow - 基于可用工具的科研查询优化管道
特性：
  - 根据工具描述优化查询
  - 严格的学术评分标准
  - 实时保存结果

Usage:
    langgraph dev
"""

import os
import json
import re
import sys
import asyncio
from dataclasses import dataclass, field
from typing import Annotated, Sequence, Literal
from dotenv import load_dotenv
import requests
from datetime import datetime
from time import sleep
from config import Config, LLMServerInfo
from prompts import (
    GENERATE_SYSTEM, 
    GENERATE_USER, 
    CRITIC_SYSTEM, 
    CRITIC_USER,
)

load_dotenv()

# ==================== Config ====================
with open("../../api_key.json") as f: json_key = json.load(f)
key = {}
for k in ['cstcloud', 'deepseek']:
    for m in json_key[k]['models']:
        key[m] = {"base_url": json_key[k]['domain'], "api_key": json_key[k]['key']}

config = Config.from_yaml("chemistry.yaml")

from dataclasses import dataclass, field
from typing import Annotated, Sequence, TypedDict, Dict

# ==================== State ====================
@dataclass
class InputState:
    """用户输入状态 - 仅接收两个字段"""
    query_id: int = field(default=0, metadata={"description": "user query"})
    query: str = field(default="", metadata={"description": "user query"})


@dataclass
class State:
    """完整工作流状态"""
    query_id: int = 0
    results: list = field(default_factory=list)
    prev_query: str = ""
    query: str = ""
    generated: str = ""
    score: float = 0.0
    tools_used: list = field(default_factory=list)


# ==================== Utilities ====================
def extract_json(text: str) -> dict:
    """从文本中提取 JSON 对象"""
    if not text:
        return {}
    
    try:
        return json.loads(text)
    except Exception:
        pass
    
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    
    try:
        candidate = text[start:end+1].replace("'", '"')
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
        return json.loads(candidate)
    except Exception:
        return {}


def load_tools(tools_file: str) -> list:
    """加载工具描述文件"""
    if not tools_file or not os.path.exists(tools_file):
        print(f"⚠️  工具文件不存在: {tools_file}")
        return []
    
    try:
        with open(tools_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        tools = data if isinstance(data, list) else data.get("tools", [])
        print(f"✅ 加载了 {len(tools)} 个工具")
        return tools
    except Exception as e:
        print(f"❌ 加载工具文件失败: {e}")
        return []


def format_tools_context(tools: list[dict[str, str]]) -> str:
    """格式化工具信息供提示词使用"""
    if not tools:
        return "（未提供工具列表）"
    
    lines = ["可用工具清单："]
    for tool in tools:
        name = tool.get("name", "unknown")
        desc = tool.get("description", "no description")
        lines.append(f"  - {name}: {desc}")
    
    return "\n".join(lines)


def extract_queries(input_data: str) -> list:
    """提取 queries 列表"""
    input_data = input_data.strip()
    
    if input_data.endswith('.json') and os.path.exists(input_data):
        with open(input_data, 'r', encoding='utf-8') as f:
            input_data = f.read()
    
    try:
        parsed = json.loads(input_data)
        if isinstance(parsed, list):
            return [q.strip() for q in parsed if isinstance(q, str) and q.strip()]
        if isinstance(parsed, dict):
            queries = parsed.get("queries") or parsed.get("query", [])
            if isinstance(queries, list):
                return [q.strip() for q in queries if isinstance(q, str) and q.strip()]
            return [queries.strip()] if isinstance(queries, str) else []
    except json.JSONDecodeError:
        pass
    
    return [input_data] if input_data else []


def save_result(result: dict, file_path: str) -> None:
    """实时保存单个结果"""
    try:        
        with open(file_path, 'a+', encoding='utf-8') as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
    except KeyboardInterrupt:
        raise
    except Exception:
        pass


# ==================== DeepSeek Client ====================
class DeepSeekClient:
    def __init__(self, info: LLMServerInfo, generate: bool = True, retry: int = 5, timeout: int = 600):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {info.api_key}",
            "Content-Type": "application/json"
        })
        self.url = f"{info.base_url.rstrip('/')}/v1/chat/completions"
        self.model = info.model
        self.retry = retry
        self.timeout = timeout
        self.generate_mode = generate
    
    def call(self, messages: list, temp: float = 0.7, max_tok: int = 1024) -> str:
        """调用 API"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_tok
        }
        
        for attempt in range(self.retry):
            try:
                sleep(1.5 * attempt)
                resp = self.session.post(self.url, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                parsed = extract_json(resp.json()["choices"][0]["message"]["content"])
                if self.generate_mode:                    
                    return parsed['optimized_query'], parsed['tools_required']
                assert '总分' in parsed
                if isinstance(parsed['总分'], str): parsed['总分'] = int(parsed['总分'])
                assert isinstance(parsed['总分'], int)
                return parsed
            except KeyboardInterrupt:
                raise
            except Exception as e:
                if attempt == 0: print(f"{'Generate' if self.generate_mode else 'Critic'} {e}")


model = LLMServerInfo(
    base_url=key[config.model]['base_url'], 
    api_key=key[config.model]['api_key'],
    model=config.model
)
critic_model = LLMServerInfo(
    base_url=key[config.critic_model]['base_url'], 
    api_key=key[config.critic_model]['api_key'],
    model=config.critic_model
)
client = DeepSeekClient(model)
critic_client = DeepSeekClient(critic_model, generate=False)
queries = extract_queries(config.input_file)
tools = load_tools(config.tool_file)
tools_context = format_tools_context(tools)


# ==================== Nodes ====================
def generate_node(state: State) -> State:
    """生成工具感知的优化查询 - 必须使用 3 个工具"""
    # 初始化状态
    state.generated, state.tools_used = "", []
    
    # 每轮都要设置当前查询，因为可能从 output_node 循环回来。
    prev_query = state.query if not state.results else state.results[-1]['optimized']
    if state.results:
        prev_query = state.results[-1]['optimized']
        critic = state.results[-1]['critic']
        critic_str = f"原始查询的评议结果：\n{json.dumps(critic, ensure_ascii=False, indent=2)}\n\n请根据评议结果"
    else:
        critic_str = "请根据上述工具"
    user = GENERATE_USER.format(tools=tools_context, query=prev_query, critic=critic_str)

    messages = [
        {"role": "system", "content": GENERATE_SYSTEM},
        {"role": "user", "content": user}
    ]        
    # 一步到位
    response = client.call(messages, temp=0.6, max_tok=4096)
    # print(f"==============Iteration {len(state.results) + 1}==============\n{response}")
    if response is not None:
        state.generated, state.tools_used = response
    print(f"query {state.query_id} iteration {len(state.results) + 1}")
    return state


def critic_node(state: State) -> State:
    """严格的学术评分 - 工具利用比重提升"""
    tools_used = state.tools_used
    generated = state.generated    
    if not generated: return state
    tools_info = "\n".join([f"  - {t['name']}: {t['description']}" for t in tools]) if tools else "无"
    
    system_prompt = CRITIC_SYSTEM    
    user_prompt = CRITIC_USER.format(
        tools_info=tools_info, 
        query=generated, 
        num_tools=len(tools_used),
        tools_used=', '.join(tools_used) if tools_used else '无'
    )    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    critic = critic_client.call(messages, temp=0, max_tok=4096)
    # print(f"==============Critic {len(state.results) + 1}==============\n{critic}")
    if critic is not None:    
        state.score = critic['总分']
        result = {
            "optimized": state.generated,
            "score": state.score,
            "tools_used": state.tools_used,
            "critic": critic,
        }    
        state.results.append(result)
    print(f"critic {state.query_id} iteration {len(state.results) + 1}")
    return state


def should_continue(state: State) -> Literal["output", "generate"]:
    """严格的质量判定"""
    if (state.score >= 80 and len(state.tools_used) == 3) or len(state.results) >= 10: return "output"  
    return "generate"


def output_node(state: State) -> State:   
    print(f"==============Conclude query {state.query_id}.==============") 
    result = {
        "id": state.query_id,
        "total_iterations": len(state.results),
        "original_query": state.query,
        "final_version": state.generated,
        "score": state.score,
        "tools_used": state.tools_used,
        "detailed_results": state.results
    }
    save_result(result, config.workflow_output)    
    return state


# ==================== Graph ====================
def create_graph():
    """创建工作流图 - 使用 InputState 作为输入"""
    from langgraph.graph import StateGraph, END
    
    # 使用 InputState 作为输入，State 作为完整状态
    workflow = StateGraph(State, input_schema=InputState)
    
    workflow.add_node("generate", generate_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("output", output_node)
    
    # 从输入直接进入 generate
    workflow.set_entry_point("generate")
    workflow.add_edge("generate", "critic")
    workflow.add_conditional_edges(
        "critic",
        should_continue,
        {"generate": "generate", "output": "output"}
    )
    workflow.add_edge("output", END)    
    return workflow.compile()


async def main():  
    workflow = create_graph() 
    await asyncio.gather(*[workflow.ainvoke({"query": q, "query_id": i}) for i, q in enumerate(queries)])


if __name__ == "__main__":
    asyncio.run(main())
