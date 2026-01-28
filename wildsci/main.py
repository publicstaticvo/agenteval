import re
import json
import os, glob
import asyncio, aiofiles
from typing import Dict, List, Any, Optional

from config import Config
from search import process_paper
from utils import skeleton_to_text
from session_manager import SessionManager, openalex_search_paper
from llm_client import Generate, Filter, Rewrite, Tester, ScientificSignificance, Critic

config = Config.from_yaml("config.yaml")
_file_lock = asyncio.Lock()


async def searchquery(query_id: int, query: str, papers_per_query: int = 200):
    """主入口：搜索并下载论文"""
    print(f"Searching papers for {query} ...")
    
    # 1. 调用异步搜索 OpenAlex
    filters = {"default.search": query, "concepts.id": "C192562407"}
    search_result = await openalex_search_paper("works", filter=filters, per_page=papers_per_query)
    search_result = search_result.get("results", [])
    print(f"Search papers for {query}, get {len(search_result)} results")
        
    # 2. 并发处理所有论文的所有 URL，每处理成功一个就ainvoke一个子图
    session = SessionManager.get()
    async def process_single_paper(i, paper_meta):
        if not paper_meta: return False
        try:
            paper_data = await process_paper(session, paper_meta)  # title, abstract, url, skeleton
            if paper_data:
                print(f"Paper {paper_meta['title']} ready. Ainvoke a generate loop.")
                with open(f"papers/Paper_q{query_id}p{i}.json", "w") as f: 
                    paper_data['id'] = f"q{query_id}p{i}"
                    if not paper_data['title']: paper_data['title'] = paper_meta['title']
                    json.dump(paper_data, f, indent=2, ensure_ascii=False)
                await generateloop(paper_data)
                # await selectnode(query_id, query, i, paper_data)              
                print(f"Paper {paper_meta['title']} loop concludes.")
        except Exception as e:
            print(f"Metadata {i} of query id {query_id} query {query} fails an {e}")

    tasks = []
    for i, paper_meta in enumerate(search_result):
        # 为每篇论文创建任务（内部会尝试所有 URL）
        tasks.append(asyncio.create_task(process_single_paper(i, paper_meta)))
    
    await asyncio.gather(*tasks)


async def generate(content: dict[str, Any]):
    model = Generate(config.generate_model, 1800)
    try:
        generated = await model.call(inputs=content)
        return generated
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"GenerateNode {e}")
        return
    

async def filter_specific(generated: list[dict[str, any]]):
    tasks = [asyncio.create_task(Filter(config.support_model).call(inputs=g, temperature=0, max_tokens=512)) for g in generated]
    questions = []
    for g, task in zip(generated, asyncio.as_completed(tasks)):
        try:
            eliminate = await task
            if isinstance(eliminate, bool) and not eliminate: questions.append(g)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"FilterNode {e}")
    return questions
    # eliminate = await asyncio.gather(*tasks, return_exceptions=True)
    # return [x for x, y in zip(generated, eliminate) if not y]


async def rewrite(generated: list[dict[str, any]]):
    tasks = [asyncio.create_task(Rewrite(config.generate_model).call(inputs=g)) for g in generated]
    refine = []
    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            if result: refine.append(result)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"RewriteNode {e}")
    return refine
    # refine = await asyncio.gather(*tasks, return_exceptions=True)
    # return [x for x in refine if isinstance(x, dict) and x]


async def test(generated: dict[str, any]):
    tasks = []
    for c in config.critic_models:
        tasks.append(asyncio.create_task(Tester(c).call(inputs=generated, top_p=0.95, max_tokens=8192)))
    # c.model: [] for c in config.critic_models
    answers = {}
    K_count = 0
    for task in asyncio.as_completed(tasks):
        try:
            c, result = await task
            answers[c] = result
            if result == "K": K_count += 1
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"TestNode {e}")
            K_count += 1
    if K_count >= len(tasks) / 2: return {"query": generated, "answers": answers} 


async def further_rewrite(generated: list[dict[str, any]]):
    tasks = [asyncio.create_task(ScientificSignificance(config.generate_model).call(inputs=g)) for g in generated]
    refine = []
    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            if result: refine.append(result)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"RewriteNode2 {e}")
    return refine


async def critic(generated: dict[str, any]):
    tasks = [asyncio.create_task(Critic(c).call(inputs=generated, top_p=0.95, max_tokens=8192)) for c in config.critic_models]
    answers = {}
    K_count = 0
    for task in asyncio.as_completed(tasks):
        try:
            c, result = await task
            answers[c] = result
            if result['selected_answer'] == "K": K_count += 1
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"CriticNode {e}")
            K_count += 1
    return {"query": generated, "answers": answers, "drop": K_count >= len(tasks) / 2} 


async def generateloop(paper: dict[str, Any]):
    # generate
    content = skeleton_to_text(paper['structure'])
    generated = await generate(content)  
    print(f"paper {paper['id']} get {len(generated)} problems")
    if not generated: return

    # filter
    filtered_generated = await filter_specific(generated)
    print(f"paper {paper['id']} get {len(filtered_generated)} valid problems")
    if not filtered_generated: return

    # refine
    refine = await rewrite(filtered_generated)
    print(f"paper {paper['id']} get {len(refine)} refined problems")
    if not refine: return

    # # test
    # tasks = [asyncio.create_task(test(g)) for g in refine]
    # tested_generated = []
    # for task in asyncio.as_completed(tasks):
    #     try:
    #         result = await task
    #         if result: tested_generated.append(result)
    #     except KeyboardInterrupt:
    #         raise
    #     except Exception as e:
    #         print(f"TestNode {e}")
    #         continue
    # print(f"paper {paper['id']} get {len(tested_generated)} answerable problems")
    # if not tested_generated: return

    # 2ND refine
    refine2nd = await further_rewrite(refine)
    print(f"paper {paper['id']} get {len(refine2nd)} scientific significance problems")
    if not refine2nd: return

    # Critic
    tasks = [asyncio.create_task(critic(g)) for g in refine2nd]
    tested_generated = []
    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            if result: tested_generated.append(result)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"CriticNode {e}")
            continue

    async with _file_lock:
        async with aiofiles.open(config.workflow_output, "a+", encoding='utf-8') as f:
            for result in tested_generated:
                result['paper_id'] = paper['id']
                result['title'] = paper['title']
                await f.write(json.dumps(result, ensure_ascii=False) + "\n")


async def gen():
    try:
        await SessionManager.init()
        if os.path.exists(config.workflow_output): os.remove(config.workflow_output)
        tasks = []
        for i, n in enumerate(glob.glob(f"{config.input_file}/*.json")):
            with open(n, encoding='utf-8') as f: paper = json.load(f)
            paper['id'] = i
            tasks.append(asyncio.create_task(generateloop(paper)))
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        await SessionManager.close()


async def debug_test():
    try:
        await SessionManager.init()
        tasks = []
        with open(config.workflow_output, encoding='utf-8') as f:
            for x in f:
                if x.strip():
                    tasks.append(asyncio.create_task(test(json.loads(x.strip())['query'])))
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        await SessionManager.close()


async def search():
    try:
        await SessionManager.init()
        queries = ["graphene", "thermal conductivity", "electric properties", "quantum transport", "light-matter interaction"]
        tasks = [asyncio.create_task(searchquery(i, q)) for i, q in enumerate(queries)]
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        await SessionManager.close()


if __name__ == "__main__":
    asyncio.run(search())
