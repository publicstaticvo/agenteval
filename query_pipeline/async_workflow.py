import json
import asyncio, aiofiles

from langgraph.types import Send
from langgraph.graph import StateGraph, START, END

from config import Config
from search import SearchNode
from session_manager import SessionManager
from generate_loop import GenerateNode, CriticNode, SelectNode
from utils import extract_queries, load_tools, format_tools_context
from state import InputState, GenerateState, GeneratePayload, AgentState

config = Config.from_yaml("chemistry.yaml")
queries = extract_queries(config.input_file)
tools = load_tools(config.tool_file)
tools_desc = format_tools_context(tools)
_file_lock = asyncio.Lock()
    

def stop_condition(state: GenerateState):
    """严格的质量判定"""
    if not (all_results := state.get('results', [])): return "generate" 
    score = all_results[-1]['score']
    tools_used = state.get('tools_used', [])
    results = state.get('results', [])
    
    if (score >= 90 and len(tools_used) >= 3) or len(results) >= 10: return "save"  
    return "generate"


async def save_node(state: GenerateState):
    async with _file_lock:
        async with aiofiles.open(config.workflow_output, "a+", encoding="utf-8") as f:
            content = json.dumps({
                "query": state.query,
                "query_id": state.query_id,
                "paper_id": state.paper_id,
                "paper_title": state.paper['title'],
                "paper_url": state.paper['url'],
                "total_iterations": len(state.results),
                "final_version": state.generated,
                "score": state.results[-1]['total_score'],
                "tools_used": state.tools_used,
                "detailed_results": state.results
            }, ensure_ascii=False)
            await f.write(content + "\n")


def build_workflow():
    # init
    select_node = SelectNode(config.model)
    generate_node = GenerateNode(config.model, tools_desc)
    critic_node = CriticNode(config.critic_model, tools_desc)

    sub_builder = StateGraph(GenerateState, input_schema=GeneratePayload)
    sub_builder.add_node("select", select_node)
    sub_builder.add_node("generate", generate_node)
    sub_builder.add_node("critic", critic_node)
    sub_builder.add_node("save", save_node)
    sub_builder.set_entry_point("select")
    sub_builder.add_edge("select", "generate")
    sub_builder.add_edge("generate", "critic")
    sub_builder.add_conditional_edges("critic", stop_condition)
    sub_builder.set_finish_point("save")
    sub_flow = sub_builder.compile()

    search_node = SearchNode()
    builder = StateGraph(AgentState, input_schema=InputState)
    builder.add_node("search",  search_node)
    builder.add_node("gen_sub", sub_flow)
    builder.add_edge(START, "search")
    builder.add_conditional_edges(
        "search",
        lambda state: [Send("gen_sub", {
            "query_id": state['query_id'], 
            "query": state['query'], 
            "paper_id": i, 
            "paper": paper}) for i, paper in enumerate(state['retrieved_papers'])]
    )
    builder.add_edge("gen_sub", END)
    return builder.compile()


async def main():
    try:
        await SessionManager.init()
        app = build_workflow()
        await asyncio.gather(*[app.ainvoke({"query_id": i, "query": q}) for i, q in enumerate(queries)])
    finally:
        await SessionManager.close()


if __name__ == "__main__":
    asyncio.run(main())
