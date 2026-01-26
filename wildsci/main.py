import re
import json
import os, glob
import asyncio, aiofiles
from typing import Dict, List, Any, Optional

from config import Config
from utils import skeleton_to_text
from session_manager import SessionManager
from llm_client import Generate, Filter, Rewrite, Tester, ScientificSignificance, Critic

config = Config.from_yaml("config.yaml")
_file_lock = asyncio.Lock()


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


if __name__ == "__main__":
    asyncio.run(gen())
