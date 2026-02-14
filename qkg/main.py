import re
import json
import os, glob
import asyncio, aiofiles
from typing import Dict, List, Any
from tenacity import RetryError

from search import process_paper
from utils import skeleton_to_text
from session_manager import SessionManager, openalex_search_paper
from llm_client.generate import generate
from llm_client.valid import valid_check, filter_specific
from llm_client.perturb import perturb, perturbcheck
from llm_client.knowledge_unit import structure, filter_structure, upgrade, upgraderank
from prompts import config

_file_lock = asyncio.Lock()


async def searchquery(query_id: int, query: str, papers_per_query: int = 200):
    """主入口：搜索并下载论文"""
    print(f"Searching papers for {query} ...")
    
    # 1. 调用异步搜索 OpenAlex
    filters = {
        "title_and_abstract.search": query, 
        "concepts.id": "C41008148", 
        "from_publication_date": "2016-01-01"
    }
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
                mechanism_units = await structure(paper_meta["structure"])
                paper_meta['mechanisms'] = mechanism_units
                with open(f"{config.paper_dir}/q{query_id}p{i}.json", "w") as f: 
                    paper_data['id'] = f"q{query_id}p{i}"
                    if not paper_data['title']: paper_data['title'] = paper_meta['title']
                    json.dump(paper_data, f, indent=2, ensure_ascii=False)
                # await generateloop(paper_data)
                print(f"Paper {paper_meta['title']} loop concludes.")
        except Exception as e:
            print(f"Metadata {i} of query id {query_id} query {query} fails an {e}")

    tasks = []
    for i, paper_meta in enumerate(search_result):
        # 为每篇论文创建任务（内部会尝试所有 URL）
        tasks.append(asyncio.create_task(process_single_paper(i, paper_meta)))
    
    await asyncio.gather(*tasks)


async def perturbloop(unit: Dict[str, Any]):
    # perturb
    perturbs = await perturb(unit)
    count = [0, 0, 0, 0, 0]
    for x in perturbs: count[int(x['level'][1]) - 1] += 1
    print(f"Unit {unit['id']} perturbs lvl {5 if unit['L5'] else 4} distribution {count}")
    if not perturbs: return

    tasks, valid_perturbs = [], []
    tasks = [asyncio.create_task(perturbcheck(g, unit)) for g in perturbs]
    for task in asyncio.as_completed(tasks):
        if result := await task: valid_perturbs.append(result)

    async with _file_lock:
        async with aiofiles.open(config.temp_output, "a+", encoding='utf-8') as f:
            for result in valid_perturbs:
                result['id'] = unit['id']
                result['title'] = unit['title']
                await f.write(json.dumps(result, ensure_ascii=False) + "\n")


async def generateloop(unit: Dict[str, Any]): 
    # generate
    generated = await generate(unit)  
    print(f"Unit {unit['id']} has {len(generated)} problems")
    if not generated: return

    # filter
    filtered_generated = await filter_specific(generated)
    print(f"Unit {unit['id']} has {len(filtered_generated)} valid problems")
    if not filtered_generated: return

    async with _file_lock:
        async with aiofiles.open(config.temp_output, "a+", encoding='utf-8') as f:
            for result in filtered_generated:
                result['id'] = unit['id']
                result['title'] = unit['title']
                await f.write(json.dumps(result, ensure_ascii=False) + "\n")

    # valid_check + Critic
    tasks = [asyncio.create_task(valid_check(g)) for g in filtered_generated]
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
    print(f"Unit {unit['id']} get {len(tested_generated)} valid problems")

    async with _file_lock:
        async with aiofiles.open(config.workflow_output, "a+", encoding='utf-8') as f:
            for result in tested_generated:
                result['id'] = unit['id']
                result['title'] = unit['title']
                await f.write(json.dumps(result, ensure_ascii=False) + "\n")


async def gen():
    try:
        await SessionManager.init()
        if os.path.exists(config.temp_output): os.remove(config.temp_output)
        if os.path.exists(config.workflow_output): os.remove(config.workflow_output)
        tasks = []
        for i, n in enumerate(glob.glob(f"{config.paper_dir}/*.json")):
            with open(n, encoding='utf-8') as f: paper = json.load(f)
            for j, u in enumerate(paper['mechanisms']):
                u['id'] = f"{i}-{j}"
                u['title'] = paper['title']
                tasks.append(asyncio.create_task(perturbloop(u)))
        await asyncio.gather(*tasks)
    except asyncio.CancelledError: pass
    except RetryError: pass
    finally: await SessionManager.close()


async def debug_test():
    try:
        await SessionManager.init()
        if os.path.exists(config.workflow_output): os.remove(config.workflow_output)
        origins = {}
        for i, n in enumerate(glob.glob(f"{config.paper_dir}/*.json")):
            with open(n, encoding='utf-8') as f: paper = json.load(f)
            for j, u in enumerate(paper['mechanisms']): origins[f"{i}-{j}"] = u
        tasks = []
        with open(config.temp_output, encoding='utf-8') as f:
            for x in f:
                if x.strip():
                    x = json.loads(x.strip())
                    tasks.append(asyncio.create_task(perturbcheck(x, origins[x['id']])))
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                if result:
                    with open(config.workflow_output, 'a+', encoding='utf-8') as f: 
                        f.write(json.dumps(result, ensure_ascii=False) + "\n")
            except Exception as e:
                print(e, type(e))
    except asyncio.CancelledError: pass
    except RetryError as e: pass
    finally: await SessionManager.close()


async def search():
    try:
        await SessionManager.init()
        # queries = ["graphene", "thermal conductivity", "electric properties", "quantum transport", "light-matter interaction"]
        queries = [
            "mechanism of in-context learning", 
            "emergent abilities scaling laws", 
            "benchmark overfitting in machine learning", 
            "failure modes of large language models", 
            "scientific method in machine learning"
        ]
        tasks = [asyncio.create_task(searchquery(i, q, 40)) for i, q in enumerate(queries)]
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        await SessionManager.close()


async def struct():
    async def _structure_wrap(paper):
        content = skeleton_to_text(paper['structure'])
        
        units = await structure(content)
        print(f"Paper {paper['id']} has {len(units)} units")

        units_keep = await filter_structure(units)
        print(f"Paper {paper['id']} has {len(units_keep)} valid units")

        upgrades = await upgrade(units_keep)
        print(f"Paper {paper['id']} has {len(upgrades)} upgrade units")

        upgrades_keep = await filter_structure(upgrades)
        print(f"Paper {paper['id']} has {len(upgrades_keep)} valid upgrade units")

        ranked = await upgraderank(upgrades_keep)
        count = [0, 0]
        for x in ranked: count[int(x['L5'])] += 1
        print(f"Paper {paper['id']} upgrade units ranked {count}")

        paper['mechanisms'] = ranked
        return paper

    try:
        await SessionManager.init()
        tasks = []
        for n in glob.glob(f"{config.paper_dir}/*.json"):
            with open(n, encoding='utf-8') as f: paper = json.load(f)
            tasks.append(asyncio.create_task(_structure_wrap(paper)))
        for task in asyncio.as_completed(tasks):
            paper = await task
            with open(f"{config.paper_dir}/Paper_{paper['id']}.json", 'w', encoding='utf-8') as f: 
                json.dump(paper, f, ensure_ascii=False, indent=2)
    finally:
        await SessionManager.close()


if __name__ == "__main__":
    asyncio.run(debug_test())
