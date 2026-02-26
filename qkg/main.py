import re
import sys
import json
import signal
import os, glob
import asyncio, aiofiles
from typing import Dict, List, Any
from tenacity import RetryError

from search import process_paper
from llm_client.generate import generate, valid
from llm_client.valid import valid_check
from llm_client.perturb import perturb, perturbcheck
from llm_client.knowledge_unit import structure, filter_structure, upgrade, upgraderank
from utils import skeleton_to_text, handle_exception, shutdown, signal_handler
from session_manager import SessionManager, openalex_search_paper
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
    unit_id = unit['id']
    del unit['id']
    # perturb
    perturbs = await perturb(unit)
    count = [0, 0, 0]
    for x in perturbs: count[int(x['perturb']['level'][1]) - 1] += 1
    print(f"Unit {unit_id} perturbs lvl 3 distribution {count}")
    if not perturbs: return

    async with _file_lock:
        async with aiofiles.open(config.temp_output, "a+", encoding='utf-8') as f:
            for result in perturbs:
                await f.write(json.dumps({**result, "id": unit_id}, ensure_ascii=False) + "\n")

    tasks, valid_perturbs = [], []
    tasks = [asyncio.create_task(perturbcheck(g, unit)) for g in perturbs]
    for task in asyncio.as_completed(tasks):
        if result := await task: valid_perturbs.append(result)
    print(f"Unit {unit_id} get {len(valid_perturbs)} valid perturbs")
    if not valid_perturbs: return

    async with _file_lock:
        async with aiofiles.open(config.workflow_output, "a+", encoding='utf-8') as f:
            for result in valid_perturbs:
                result['id'] = unit_id
                await f.write(json.dumps(result, ensure_ascii=False) + "\n")


async def generateloop(unit: Dict[str, Any]): 
    # normalization
    def _normfm(fm):
        if isinstance(fm, dict):
            break_condition = fm.get("original_break_condition", "").strip()
            if break_condition[-1] == '.': break_condition = break_condition[:-1]
            violation = fm.get("violation_description", "").strip()
            if violation[-1] == '.': violation = violation[:-1]

            if break_condition and violation:
                return f"Fails WHEN {break_condition} BECAUSE {violation}."
            elif break_condition:
                return f"Fails WHEN {break_condition}."
            elif violation:
                return f"Failure occurs BECAUSE {violation}."
            else:
                return "Failure under unspecified boundary."
        else:
            return fm

    unit['new']['failure_modes'] = [_normfm(x) for x in unit['new']['failure_modes']]
    # generate    
    if not (generated := await generate(unit['new'])): return
    result = await valid(generated)
    generated = {"status": result, **generated}

    async with _file_lock:
        async with aiofiles.open(config.temp_output, "a+", encoding='utf-8') as f:
            await f.write(json.dumps(generated, ensure_ascii=False) + "\n")

    # valid_result = await valid_check(generated)
    # if isinstance(valid_result, dict):
    #     generated = valid_result
    # generated['unit'] = unit
    return generated


async def per():
    if os.path.exists(config.temp_output): os.remove(config.temp_output)
    if os.path.exists(config.workflow_output): os.remove(config.workflow_output)
    tasks = []
    for i, n in enumerate(glob.glob(f"{config.paper_dir}/*.json")):
        with open(n, encoding='utf-8') as f: paper = json.load(f)
        for j, u in enumerate(paper['mechanisms']):
            u['id'] = f"{i}-{j}"
            # u['title'] = paper['title']
            tasks.append(asyncio.create_task(perturbloop(u)))
    await asyncio.gather(*tasks)


async def debug_test():
    if os.path.exists(config.workflow_output): os.remove(config.workflow_output)
    origins = {}
    for i, n in enumerate(glob.glob(f"{config.paper_dir}/*.json")):
        with open(n, encoding='utf-8') as f: paper = json.load(f)
        for j, u in enumerate(paper['mechanisms']): origins[f"{i}-{j}"] = u
    tasks, items = [], []
    with open(config.temp_output, encoding='utf-8') as f:
        for x in f:
            if x.strip():
                x = json.loads(x.strip())
                if "ReverseConsistency" in x['status'] or x['status'] == "Majority select False":
                    del x['status']
                    if 'reason' in x: del x['reason']
                    if "model_results" in x: del x["model_results"]
                    items.append(x)
                    tasks.append(asyncio.create_task(valid(x)))
    import tqdm
    for x, task in tqdm.tqdm(zip(items, asyncio.as_completed(tasks)), total=len(tasks)):
        try:
            result = await task
            if result:
                x = {"status": result, **x}
                with open(config.workflow_output, 'a+', encoding='utf-8') as f: 
                    f.write(json.dumps(x, ensure_ascii=False) + "\n")
        except Exception as e:
            print(e, type(e))
            

async def gen():
    if os.path.exists(config.temp_output): os.remove(config.temp_output)
    if os.path.exists(config.workflow_output): os.remove(config.workflow_output)
    tasks = []
    with open("mechanisms.jsonl", encoding='utf-8') as f:
        for x in f:
            if x.strip():
                x = json.loads(x.strip())
                del x['new']['minimal_example']
                tasks.append(asyncio.create_task(generateloop(x)))
    # with open("mechanisms.jsonl", encoding='utf-8') as f:
    #     d = [json.loads(x.strip()) for x in f if x.strip()]
    # tasks = [asyncio.create_task(generateloop(d[1])) for _ in range(10)]
    import tqdm
    for task in tqdm.tqdm(asyncio.as_completed(tasks), total=len(tasks)):
        try:
            result = await task
            if result:
                with open(config.workflow_output, 'a+', encoding='utf-8') as f: 
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
        except Exception as e:
            print(e, type(e))


async def search():
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

        # ranked = await upgraderank(upgrades_keep)
        # count = [0, 0]
        # for x in ranked: count[int(x['L5'])] += 1
        # print(f"Paper {paper['id']} upgrade units ranked {count}")

        paper['mechanisms'] = upgrades_keep
        return paper

    tasks = []
    for n in glob.glob(f"{config.paper_dir}/*.json"):
        with open(n, encoding='utf-8') as f: paper = json.load(f)
        tasks.append(asyncio.create_task(_structure_wrap(paper)))
    for task in asyncio.as_completed(tasks):
        paper = await task
        with open(f"{config.paper_dir}/Paper_{paper['id']}.json", 'w', encoding='utf-8') as f: 
            json.dump(paper, f, ensure_ascii=False, indent=2)


async def main():
    # import warnings
    # warnings.filterwarnings("ignore", message="Task was destroyed but it is pending")
    # if sys.platform == 'win32':
    #     # Windows: 使用 signal.signal
    #     signal.signal(signal.SIGINT, signal_handler)
    #     signal.signal(signal.SIGTERM, signal_handler)
    # else:
    #     # Unix/Linux/Mac: 使用 add_signal_handler
    #     loop = asyncio.get_running_loop()
    #     for sig in (signal.SIGINT, signal.SIGTERM):
    #         loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown()))
    try:
        await SessionManager.init()
        await struct()
    except asyncio.CancelledError: pass
    except RetryError: pass
    finally: await SessionManager.close()


if __name__ == "__main__":
    asyncio.run(main())
