import re
import json
import os, glob
import asyncio, aiofiles
from tenacity import RetryError
from typing import Dict, List, Any, Optional

from config import Config
from search import process_paper
from utils import skeleton_to_text
from session_manager import SessionManager, openalex_search_paper
from llm_client import Generate, Filter, Rewrite, Assumption, Graph, Tester

config = Config.from_yaml("config.yaml")
_file_lock = asyncio.Lock()
GREEDY_PARAMS = {
    'temperature': 0.0, "max_tokens": 8192, "seed": 42,
    "top_p": 1.0,      # 设置为1，不进行核采样
    "top_k": 1,        # 或设置为1，确保总是选择最可能的token
    "repetition_penalty": 1.0,  # 设置为1，禁用重复惩罚
    "length_penalty": 1.0,      # 设置为1，禁用长度惩罚
    "no_repeat_ngram_size": 0,  # 设置为0，禁用n-gram重复惩罚
}
SAMPLE_PARAMS = {'temperature': 0.8, "max_tokens": 8192, "top_p": 0.95}


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
    model = Generate(config.generate_model, SAMPLE_PARAMS, 1800)
    try:
        generated = await model.call(inputs=content)
        return generated
    except Exception as e:
        print(f"GenerateNode {e}")
        return
    

async def filter_specific(generated: list[dict[str, any]]):
    tasks = [asyncio.create_task(Filter(config.support_model, GREEDY_PARAMS).call(inputs=g, max_tokens=512)) for g in generated]
    questions = []
    for g, task in zip(generated, asyncio.as_completed(tasks)):
        try:
            eliminate = await task
            if isinstance(eliminate, bool) and not eliminate: questions.append(g)
        except Exception as e:
            print(f"FilterNode {e}")
    return questions


async def rewrite(generated: list[dict[str, any]]):
    tasks = [asyncio.create_task(Rewrite(config.generate_model, SAMPLE_PARAMS).call(inputs=g)) for g in generated]
    refine = []
    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            if result: refine.append(result)
        except Exception as e:
            print(f"RewriteNode {e}")
    return refine


async def valid_check(generated: dict[str, any]):
    try:
        assumption, option_map = await Assumption(config.support_model, GREEDY_PARAMS).call(inputs=generated)
    except Exception as e:
        print(f"AssumtionNode {e}")
        assumption = None
        raise
    if not assumption: return {"query": generated, "drop": True, "reason": "no assumptions"}

    try:
        graph = await Graph(config.support_model, GREEDY_PARAMS).call(inputs=assumption)
    except Exception as e:
        print(f"GraphNode {e}")
        graph = None
        raise
    if not graph: return {"query": generated, "drop": True, "reason": "no graph", "assumptions": assumption, "option_map": option_map}
    
    # 四部验证法
    assignment = {k: "Self-contradict" if v['self_contradiction'] else None for k, v in graph.items()}
    # 第一步：所有题干节点，赋值为True
    for g in option_map['global']:
        if assignment[g] is not None:
            return {"query": generated, "drop": True, "reason": "self-contradicted question", "assumptions": assumption, "option_map": option_map, "graph": graph}
        assignment[g] = "True"
    # 第二步：所有与True互斥的节点，赋值为False
    for g in option_map['global']:
        for m in graph[g]['mutual_exclusivity']:
            if assignment[m] == "True":
                return {"query": generated, "drop": True, "reason": "mutual-exclusive question", "assumptions": assumption, "option_map": option_map, "graph": graph}
            elif assignment[m] is None: assignment[m] = "False"
    # 第三步：依赖False/self-contradicted的节点应为Invalid
    changed = True
    while changed:
        changed = False
        for k in graph:
            for v in graph[k]['depends_on']:
                if assignment[v] in ['False', 'Self-contradict', 'Invalid']:
                    if assignment[k] == "True":
                        return {"query": generated, "drop": True, "reason": "mutual-exclusive structure", "assumptions": assumption, "option_map": option_map, "graph": graph}
                    elif assignment[k] is None:
                        changed = True
                        assignment[k] = "Invalid"
    # 第四步：至少存在一个无False的选项
    for k in option_map:
        if k == "global": continue
        for x in option_map[k]:
            if assignment[x] in ['False', 'Self-contradict', 'Invalid']: break
        else: break
    else: return {"query": generated, "drop": True, "reason": "no correct options", "assumptions": assumption, "option_map": option_map, "graph": graph}

    # 多模型试做
    tasks = [asyncio.create_task(Tester(c, GREEDY_PARAMS).call(inputs=generated)) for c in config.critic_models]
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
            print(f"CriticNode {e}")
    return {"query": generated, "answers": answers, "drop": K_count > 0, "assumptions": assumption, "option_map": option_map, "graph": graph} 


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

    # valid_check + Critic
    tasks = [asyncio.create_task(valid_check(g)) for g in refine]
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
        if os.path.exists(config.workflow_output): os.remove(config.workflow_output)
        tasks = []
        with open("temp.jsonl") as f:
            for x in f:
                if x.strip():
                    x = json.loads(x.strip())
                    tasks.append(asyncio.create_task(valid_check(x)))
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                if not isinstance(result, dict): continue
                with open(config.workflow_output, 'a+') as f: 
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
            except Exception as e:
                print(e, type(e))
                pass
    except asyncio.CancelledError:
        pass
    except RetryError as e:
        pass
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
    asyncio.run(debug_test())
