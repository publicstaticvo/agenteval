import json
import asyncio, aiofiles
from langgraph.types import Send
from langgraph.graph import StateGraph
from typing import Dict, List, Any, Optional

from config import Config
from search import process_paper
from intro_select import SelectNode
from state import GenerateState, GeneratePayload
from generate_loop import GenerateNode, CriticNode
from session_manager import openalex_search_paper, SessionManager
from hybrid_select import HybridSelectStep1, HybridSelectStep2, HybridSelectStep3
from utils import extract_queries, load_tools, format_tools_context, skeleton_to_list, skeleton_to_dict

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
    return "generate"


async def save_node(state: GenerateState):
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
    generate_node = GenerateNode(config.model, tools_desc)
    critic_node = CriticNode(config.critic_model, tools_desc)

    workflow = StateGraph(GenerateState, input_schema=GeneratePayload)
    workflow.add_node("generate", generate_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("save", save_node)
    workflow.set_entry_point("generate")
    workflow.add_edge("generate", "critic")
    workflow.add_conditional_edges("critic", stop_condition)
    workflow.set_finish_point("save")
    return workflow.compile()


app = build_workflow()


async def selectnode(query_id, query, paper_id, paper) -> Dict[str, List[Dict[str, Any]]]:
    print(f"Select paper range for query {query_id} paper id {paper_id} title {paper['title']}")
    content, paragraphs = skeleton_to_list(paper['structure'], "full")
    try:
        candidates = await HybridSelectStep1(config.model).call(inputs={'content': content}, context={'paragraphs': paragraphs})
    except Exception as e:
        print(f"Step 1 {e}")
        candidates = []
    # with open("papers/step1.jsonl", "w") as f:
    #     for x in candidates: f.write(json.dumps(x, ensure_ascii=False) + "\n")
    # with open("papers/step1.jsonl") as f:
    #     candidates = [json.loads(line.strip()) for line in f if line.strip()]
    print(f"Paper {paper_id} {paper['title']} get {len(candidates)}")
    tasks = [asyncio.create_task(HybridSelectStep2(config.model).call(inputs=c)) for c in candidates]
    reproducible = []
    for task in asyncio.as_completed(tasks):            
        try:
            result = await task
            if result: 
                reproducible.append(result)
                with open("papers/step2.jsonl", "a+") as f:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"Step 2 {e}")
    print(f"Paper {paper_id} {paper['title']} get {len(reproducible)}")
    content = skeleton_to_dict(paper['structure'])
    tasks = [asyncio.create_task(HybridSelectStep3(config.model).call(inputs={'sentence': c, 'paper': content})) for c in reproducible]
    print(f"Paper get {len(tasks)}")
    result_and_method = []
    for task in asyncio.as_completed(tasks):            
        try:
            result = await task
            if result: 
                result_and_method.append(result)
                with open("papers/step3.jsonl", "a+") as f:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"Step 3 {e}")
    print(f"Paper {paper_id} {paper['title']} 3 get {len(result_and_method)}")
    # TODO: filter
    for i, result in enumerate(result_and_method):
        print(f"Start generate!")
        await app.ainvoke({
            "query_id": query_id, 
            "query": query, 
            "paper_id": paper_id,
            "paper": paper['title'],
            "artifact": result
        })


async def searchnode(query_id: int, query: str):
    """主入口：搜索并下载论文"""
    print(f"Searching papers for {query} ...")
    
    # 1. 调用异步搜索 OpenAlex
    search_result = await openalex_search_paper("works", filter={"default.search": query})
    search_result = search_result.get("results", [])
    print(f"Search papers for {query}, get {len(search_result)} results")
        
    # 2. 并发处理所有论文的所有 URL，每处理成功一个就ainvoke一个子图
    session = SessionManager.get()
    async def process_single_paper(i, paper_meta):
        if not paper_meta: return False
        try:
            paper_data = await process_paper(session, paper_meta)  # title, abstract, url, skeleton
            if paper_data:
                print(f"Paper {paper_data['title']} ready. Ainvoke a select loop.")
                with open(f"papers/Paper_{i}.json", "w") as f: 
                    json.dump({"id": i, "content": paper_data}, f, indent=2, ensure_ascii=False)
                # await selectnode(query_id, query, i, paper_data)              
                print(f"Paper {paper_data['title']} loop concludes.")
        except Exception as e:
            print(f"Metadata {i} of query id {query_id} query {query} fails an {e}")

    tasks = []
    for i, paper_meta in enumerate(search_result):
        # 为每篇论文创建任务（内部会尝试所有 URL）
        tasks.append(asyncio.create_task(process_single_paper(i, paper_meta)))
    
    await asyncio.gather(*tasks)


async def direct_select(query_id: int, query: str):
    import glob
    for n in glob.glob("papers/Paper_*.json"):
        print(n)
        with open(n) as f: paper = json.load(f)
        await selectnode(query_id, query, paper['id'], paper['content'])
        break


async def main():
    try:
        await SessionManager.init()
        await asyncio.gather(*[direct_select(i, query) for i, query in enumerate(queries)])
    finally:
        await SessionManager.close()


if __name__ == "__main__":
    asyncio.run(main())
