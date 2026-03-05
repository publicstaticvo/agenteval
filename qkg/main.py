import re
import sys
import json
import tqdm
import signal
import os, glob
import asyncio, aiofiles
from typing import Dict, List, Any
from tenacity import RetryError

from search import searchquery
from llm_client.generate import generateloop
from llm_client.valid import valid_check
from llm_client.perturb import perturbloop
from llm_client.knowledge_unit import structloop
from utils import skeleton_to_text, handle_exception, shutdown, signal_handler
from session_manager import SessionManager
from prompts import config


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
                    tasks.append(asyncio.create_task(valid_check(x)))
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


async def search():
    # queries = ["graphene", "thermal conductivity", "electric properties", "quantum transport", "light-matter interaction"]
    queries = [
        "causal mechanism deep learning", 
        "theoretical analysis transformer", 
        "emergent phenomenon neural networks", 
        "provable guarantees reinforcement learning", 
        "algorithmic bias explanation"
    ]
    tasks = [asyncio.create_task(searchquery(i, q, 200)) for i, q in enumerate(queries)]
    await asyncio.gather(*tasks, return_exceptions=True)


async def struct():
    if os.path.exists(config.temp_output): os.remove(config.temp_output)
    if os.path.exists(config.workflow_output): os.remove(config.workflow_output)
    tasks = []
    for n in glob.glob(f"{config.paper_dir}/*.json"):
        with open(n, encoding='utf-8') as f: paper = json.load(f)
        tasks.append(asyncio.create_task(structloop(paper)))
    for task in tqdm.tqdm(asyncio.as_completed(tasks), total=len(tasks)):
        paper = await task
        if not isinstance(paper, dict): 
            print(paper)
            continue
        with open(f"{config.paper_dir}/Paper_{paper['id']}.json", 'w', encoding='utf-8') as f: 
            json.dump(paper, f, ensure_ascii=False, indent=2)
        if 'mechanism' in paper:            
            with open(config.workflow_output, 'a+', encoding='utf-8') as f:
                f.write(json.dumps({**paper['mechanism'], "id": paper['id']}) + "\n")


async def perturb():
    if os.path.exists(config.temp_output): os.remove(config.temp_output)
    if os.path.exists(config.workflow_output): os.remove(config.workflow_output)
    tasks = []
    for n in glob.glob(f"{config.paper_dir}/*.json"):
        with open(n, encoding='utf-8') as f: paper = json.load(f)
        if 'decision' not in paper['mechanism'] or "Pass" in paper['mechanism']['decision']: 
            tasks.append(asyncio.create_task(perturbloop(paper)))
    for task in tqdm.tqdm(asyncio.as_completed(tasks), total=len(tasks)):
        paper = await task
        if not isinstance(paper, dict): 
            print(paper)
            continue
        # with open(f"{config.paper_dir}/Paper_{paper['id']}.json", 'w', encoding='utf-8') as f: 
        #     json.dump(paper, f, ensure_ascii=False, indent=2)
        with open(config.workflow_output, 'a+', encoding='utf-8') as f:
            f.write(json.dumps({**paper['mechanism'], "id": paper['id']}) + "\n")


async def gen():
    if os.path.exists(config.temp_output): os.remove(config.temp_output)
    if os.path.exists(config.workflow_output): os.remove(config.workflow_output)
    tasks = []
    with open("mechanisms.jsonl", encoding='utf-8') as f:
        for x in f:
            if x.strip():
                x = json.loads(x.strip())
                tasks.append(asyncio.create_task(generateloop(x)))
    import tqdm
    for task in tqdm.tqdm(asyncio.as_completed(tasks), total=len(tasks)):
        try:
            results = await task
            if results:
                with open(config.workflow_output, 'a+', encoding='utf-8') as f: 
                    for result in results: f.write(json.dumps(result, ensure_ascii=False) + "\n")
        except Exception as e:
            print(e, type(e))


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
        await gen()
    except asyncio.CancelledError: pass
    except RetryError: pass
    finally: await SessionManager.close()


if __name__ == "__main__":
    asyncio.run(main())
