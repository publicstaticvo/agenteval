import json
import asyncio, aiofiles
from langgraph.types import Send
from langgraph.graph import StateGraph
from typing import Dict, List, Any, Optional

from config import Config
from state import GenerateState
from search import process_paper
from llm_client import ExtractStep, ValidStep
from session_manager import openalex_search_paper, SessionManager
from utils import extract_queries, load_tools, format_tools_context, skeleton_to_list, skeleton_to_dict

config = Config.from_yaml("config.yaml")
# queries = extract_queries(config.input_file)
# tools = load_tools(config.tool_file)
# tools_desc = format_tools_context(tools)
# _file_lock = asyncio.Lock()


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
                # with open(f"Paper_{i}.json", "w") as f: 
                #     json.dump({"id": i, "content": paper_data}, f, indent=2, ensure_ascii=False)
                await selectnode(query_id, query, i, paper_data)              
                print(f"Paper {paper_data['title']} loop concludes.")
        except Exception as e:
            print(f"Metadata {i} of query id {query_id} query {query} fails an {e}")

    tasks = []
    for i, paper_meta in enumerate(search_result):
        # 为每篇论文创建任务（内部会尝试所有 URL）
        tasks.append(asyncio.create_task(process_single_paper(i, paper_meta)))
    
    await asyncio.gather(*tasks)


async def selectnode(paper_id, paper) -> Dict[str, List[Dict[str, Any]]]:
    print(f"Select for paper id {paper_id} title {paper['title']}")
    # content, paragraphs = skeleton_to_list(paper['structure'], "full")
    content = skeleton_to_dict(paper['structure'])
    inputs = []
    for section in content:
        for p in section['paragraphs']:
            inputs.append({"title": paper['title'], "name": section['section_name'], "text": p})
    step1 = ExtractStep(config.support_model)
    tasks = [asyncio.create_task(step1.call(inputs=x)) for x in inputs]
    step1_results = []
    for i, task in enumerate(asyncio.as_completed(tasks)):
        try:
            result = await task
            if result:
                with open("papers/extract_step.jsonl", "a+", encoding='utf-8') as f:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
                step1_results.append(result)
        except Exception as e:
            print(i, "Step 1", e, type(e))
    print(f"Paper id {paper_id} get {len(step1_results)} step12")
            
    # with open('papers/extract_step.jsonl', encoding='utf-8') as f: 
    #     step1_results = [json.loads(x.strip()) for x in f if x.strip()]
    step3 = ValidStep(config.critic_model)
    tasks = [asyncio.create_task(step3.call(inputs=x)) for x in step1_results]
    step3_results = []
    for i, task in enumerate(asyncio.as_completed(tasks)):
        try:
            result = await task
            if result:
                with open("papers/valid_step.jsonl", "a+", encoding='utf-8') as f:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
                step3_results.append(result)
        except Exception as e:
            print(i, "Step 3", e, type(e))
            raise
    print(f"Paper id {paper_id} get {len(step3_results)} step3")


async def main():
    try:
        await SessionManager.init()
        # await asyncio.gather(*[searchnode(i, query) for i, query in enumerate(queries)])
        import os
        # if os.path.exists(f"papers/extract_step.jsonl"): os.remove(f"papers/extract_step.jsonl")
        # with open("papers/Paper_8.json", encoding='utf-8') as f: paper = json.load(f)['content']
        # await selectnode(8, paper)
        with open("papers/Paper_13.json", encoding='utf-8') as f: paper = json.load(f)['content']
        await selectnode(13, paper)
    finally:
        await SessionManager.close()


if __name__ == "__main__":
    asyncio.run(main())
