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
from dataclasses import dataclass, field
from typing import Annotated, Sequence, Literal
from dotenv import load_dotenv
import requests
from datetime import datetime
from time import sleep
from config import Config
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
model = config.model
print(config, key[model])

runtime = datetime.now().strftime('%Y%m%d_%H%M%S')

from dataclasses import dataclass, field
from typing import Annotated, Sequence

# ==================== State ====================
@dataclass
class InputState:
    """用户输入状态 - 仅接收两个字段"""
    input_data: str = field(default=config.first_output, metadata={"description": "JSON 格式查询列表或文件路径"})
    tools_file: str = field(default=config.tool_file, metadata={"description": "工具描述 JSON 文件路径"})


@dataclass
class State:
    """完整工作流状态"""
    # 输入字段
    input_data: str = ""
    tools_file: str = ""
    
    # 内部状态
    tools: list = field(default_factory=list)
    tools_context: str = ""
    queries: list = field(default_factory=list)
    results: list = field(default_factory=list)
    output_file: str = ""
    idx: int = 0
    query: str = ""
    iteration: int = 0
    generated: str = ""
    score: float = 0.0
    feedback: str = ""
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


def format_tools_context(tools: list) -> str:
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
    except Exception as e:
        print(f"❌ 保存失败: {e}")


def finalize_output(file_path: str) -> None:
    """完成输出文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        data["status"] = "completed"
        data["completed_at"] = datetime.now().isoformat()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ 完成失败: {e}")


# ==================== DeepSeek Client ====================
class DeepSeekClient:
    def __init__(self, api_key: str, base_url: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
        self.url = f"{base_url.rstrip('/')}/v1/chat/completions"
        print(self.url)
    
    def call(self, messages: list, temp: float = 0.7, max_tok: int = 1024) -> str:
        """调用 API"""
        payload = {
            "model": config.model,
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_tok
        }
        
        for attempt in range(3):
            try:
                resp = self.session.post(self.url, json=payload, timeout=600)
                resp.raise_for_status()                
                content = resp.json()["choices"][0]["message"]["content"]
                return content
            except Exception as e:
                if attempt < 2:
                    sleep(1.5 ** (attempt + 1))
        return ""


client = DeepSeekClient(key[model]['api_key'], key[model]['base_url'])


# ==================== Nodes ====================
def generate_node(state: State) -> State:
    """生成工具感知的优化查询 - 必须使用 3 个工具"""
    # 首次调用：初始化状态
    if not state.tools:
        state.tools = load_tools(state.tools_file)
        state.tools_context = format_tools_context(state.tools)
        state.queries = extract_queries(state.input_data)
        state.results = []
        state.idx = 0
        state.output_file = config.workflow_output
        
        print(f"\n[输入] 提取 {len(state.queries)} 个查询")
        for i, q in enumerate(state.queries, 1):
            print(f"  {i}. {q}")
            if i == 10: break
        print()
    
    # 每轮都要设置当前查询，因为可能从 output_node 循环回来。
    if state.idx < len(state.queries):
        state.query = state.queries[state.idx]
        state.iteration += 1
        print(f"\n{'='*70}\n[处理] #{state.idx+1}/{len(state.queries)}: {state.query}\n[第 {state.iteration} 轮优化]\n")
    
    user = GENERATE_USER.format(tools=state.tools_context, query=state.query, critic="请根据上述工具")
    messages = [
        {"role": "system", "content": GENERATE_SYSTEM},
        {"role": "user", "content": user}
    ]
    
    raw = client.call(messages, temp=0.6, max_tok=4096)
    parsed = extract_json(raw)
    
    state.generated = parsed.get("optimized_query", raw.strip())
    state.tools_used = parsed.get("tools_required", [])
    
    print(f"[生成] 轮 {state.iteration}: {state.generated[:100]}...")
    print(f"  工具({len(state.tools_used)}): {', '.join(state.tools_used) or '无'}")
    
    return state


def critic_node(state: State) -> State:
    """严格的学术评分 - 工具利用比重提升"""
    tools = state.tools
    tools_used = state.tools_used
    generated = state.generated
    
    tools_info = "\n".join([f"  - {t.get('name')}: {t.get('description')}" 
                            for t in tools]) if tools else "无"
    
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
    
    raw = client.call(messages, temp=0.3, max_tok=1024)
    parsed = extract_json(raw)
    
    state.score = float(parsed.get("total_score", 0.0))
    state.feedback = parsed.get("detailed_feedback", "")
    
    dim_scores = parsed.get("dimension_scores", {})
    print(f"[评估] 总分: {state.score:.0f}/100")
    print(f"  学术严谨性: {dim_scores.get('academic_rigor', 0)}/25")
    ind = " ✓" if len(tools_used) == 3 else " ⚠️"
    print(f"  工具利用: {dim_scores.get('utilization', 0)}/35 | 工具数: {len(tools_used)}/3{ind}")
    print(f"  可执行性: {dim_scores.get('executability', 0)}/30")
    print(f"  创新性: {dim_scores.get('innovation_impact', 0)}/10")
    print(f"  反馈: {state.feedback}")
    
    return state


def should_continue(state: State) -> Literal["output", "generate"]:
    """严格的质量判定"""
    if state.score >= 80 and len(state.tools_used) == 3:
        print(f"[判定] ✓ 达到发表级别 (3工具 + {state.score:.0f}分) → 输出")
        return "output"
    
    if state.iteration >= 3:
        print(f"[判定] ✗ 达到最大迭代次数(3轮) → 输出")
        return "output"
    
    print(f"[判定] ✗ 未达标准 (得分 {state.score:.0f}/80, 工具 {len(state.tools_used)}/3) → 继续")
    return "generate"


def output_node(state: State) -> State:
    """输出结果并保存 - 每轮迭代都保存"""
    result = {
        "idx": state.idx + 1,
        "iteration": state.iteration,
        "original": state.query,
        "optimized": state.generated,
        "score": state.score,
        "tools_used": state.tools_used,
        "feedback": state.feedback,
        "timestamp": datetime.now().isoformat()
    }
    
    state.results.append(result)
    # 实时保存单个结果
    save_result(result, state.output_file)
    
    print(f"\n[输出] ✅ 完成优化")
    print(f"  最终得分: {state.score:.0f} | 迭代: {state.iteration}")
    print(f"  优化查询: {state.generated[:100]}...")
    
    # 重置为下一个查询做准备
    state.idx += 1
    state.iteration = 0
    state.generated = ""
    state.tools_used = []
    state.score = 0.0
    state.feedback = ""
    
    return state


def next_query(state: State) -> Literal["generate", "end"]:
    """判断是否还有查询"""
    if state.idx < len(state.queries):
        return "generate"
    
    finalize_output(state.output_file)
    
    total = len(state.results)
    passed = sum(1 for r in state.results if r.get("score", 0) >= 80)
    avg_score = sum(r.get("score", 0) for r in state.results) / total if total > 0 else 0
    total_iterations = sum(r.get("iteration", 0) for r in state.results)
    
    print(f"\n{'='*70}")
    print(f"[完成] ✅ 所有查询处理完毕")
    print(f"  总查询数: {total}")
    print(f"  达标数(≥80分): {passed}")
    print(f"  平均得分: {avg_score:.1f}/100")
    print(f"  总迭代次数: {total_iterations}")
    print(f"  结果已保存到: {state.output_file}")
    print(f"{'='*70}")
    
    return "end"


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
    workflow.add_conditional_edges(
        "output",
        next_query,
        {"generate": "generate", "end": END}
    )
    
    return workflow.compile()


create_graph().invoke({"input_data": config.input_file, "tools_file": config.tool_file})
