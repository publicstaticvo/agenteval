import json
import asyncio, aiofiles
from langgraph.graph import StateGraph, START, END

from config import Config
from search import process_paper
from state import GenerateState, GeneratePayload
from generate_loop import GenerateNode, CriticNode, SelectNode
from utils import extract_queries, load_tools, format_tools_context
from session_manager import openalex_search_paper, SessionManager, RateLimit

config = Config.from_yaml("config.yaml")
queries = extract_queries(config.input_file)
tools = load_tools(config.tool_file)
tools_desc = format_tools_context(tools)
_file_lock = asyncio.Lock()
    

def stop_condition(state: GenerateState):
    """严格的质量判定"""
    if not state.results: return "generate" 
    score = state.results[-1]['score']
    
    if (score >= 95 and len(state.tools_used) >= 3) or len(state.results) >= 10:        
        print(f"The score for query {state.query} paper {state.paper['title']} is {score}, can output now.")
        return "save"  
    print(f"The score for query {state.query} paper {state.paper['title']} is {score}, cannot output now.")
    return "generate"


async def save_node(state: GenerateState):
    if not state.sections: return
    async with _file_lock:
        async with aiofiles.open(config.workflow_output, "a+", encoding="utf-8") as f:
            content = json.dumps({
                "query": state.query,
                "query_id": state.query_id,
                "paper_title": state.paper['title'],
                "paper_url": state.paper['url'],
                "total_iterations": len(state.results),
                "final_version": state.generated,
                "score": state.results[-1]['score'],
                "tools_used": state.tools_used,
                "detailed_results": state.results
            }, ensure_ascii=False)
            await f.write(content + "\n")


def build_workflow():
    # init
    select_node = SelectNode(config.model)
    generate_node = GenerateNode(config.model, tools_desc)
    critic_node = CriticNode(config.critic_model, tools_desc)

    workflow = StateGraph(GenerateState, input_schema=GeneratePayload)
    workflow.add_node("select", select_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("save", save_node)
    workflow.set_entry_point("select")
    workflow.add_conditional_edges("select", lambda state: ("generate" if state.sections else "save"))
    workflow.add_edge("generate", "critic")
    workflow.add_conditional_edges("critic", stop_condition)
    workflow.set_finish_point("save")
    return workflow.compile()


app = build_workflow()


async def searchnode(query_id: int, query: str):
    """主入口：搜索并下载论文"""
    print(f"Searching papers for {query} ...")
    
    # 1. 调用异步搜索 OpenAlex
    async with RateLimit.SEARCH_SEMAPHORE:            # 并发量10-20
        search_result = await openalex_search_paper("works", filter={"default.search": query}, per_page=200)
    search_result = search_result.get("results", [])
    print(f"Search papers for {query}, get {len(search_result)} results")
        
    # 2. 并发处理所有论文的所有 URL，每处理成功一个就ainvoke一个子图
    session = SessionManager.get()
    async def process_single_paper(i, paper_meta):
        if not paper_meta: return False
        try:
            paper_data = await process_paper(session, paper_meta)  # title, abstract, url, skeleton
            if paper_data:
                print(f"Paper {paper_data['title']} ready. Ainvoke a generate loop.")
                await app.ainvoke({"query_id": query_id, "query": query, "paper": paper_data})
                print(f"Paper {paper_data['title']} loop concludes.")
                return True
        except Exception as e:
            print(f"Metadata {i} of query id {query_id} query {query} fails an {e}")
            raise
        return False

    tasks = []
    for i, paper_meta in enumerate(search_result):
        # 为每篇论文创建任务（内部会尝试所有 URL）
        tasks.append(asyncio.create_task(process_single_paper(i, paper_meta)))
    
    await asyncio.gather(*tasks)


async def main():
    try:
        await SessionManager.init()
        await asyncio.gather(*[searchnode(i, query) for i, query in enumerate(queries)])
    finally:
        await SessionManager.close()


if __name__ == "__main__":
    asyncio.run(main())
