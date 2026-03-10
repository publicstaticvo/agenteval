import asyncio
from tenacity import RetryError

from config import Config
from utils import load_local, print_json
from llm_client.session_manager import SessionManager
from llm_client.benchmark_test import HLETest
from llm_client.correctness_check import Correctness

config = Config.from_yaml("config.yaml")
SAMPLE_PARAMS = {'temperature': 0.8, "max_tokens": 8192, "top_p": 0.95}
GREEDY_PARAMS = {
    'temperature': 0.0, "max_tokens": 8192, "seed": 42, "repetition_penalty": 1.0,
    "length_penalty": 1.0, "no_repeat_ngram_size": 0,
}
correctness_model = Correctness(config.models[0], GREEDY_PARAMS)


async def hle(dataset, model):
    model = HLETest(model, SAMPLE_PARAMS)
    tasks = [asyncio.create_task(model.call(inputs=x)) for x in dataset]
    answers = {}
    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            if result: answers[result['id']] = result
        except Exception as e: continue
    tasks = []
    for x in dataset:
        if x['id'] not in answers: continue
        if x['answer_type'] == 'exactMatch':
            tasks.append(asyncio.create_task(correctness_model.call(inputs={"q": x, 'a': answers[x['id']]})))
        elif x['answer_type'] == 'multipleChoice':
            answers[x['id']]['eval'] = {"correct": answers[x['id']]['answer'].lower() == x['answer'].lower()}
    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            if result: answers[result['id']]['eval'] = result
        except Exception as e: continue
    return answers, model


async def test():
    try:
        await SessionManager.init()
        d = load_local(config.test_input)
        tasks = [asyncio.create_task(hle(d, m)) for m in config.models]
        answers = {}
        for task in asyncio.as_completed(tasks):
            try:
                result, model = await task
                for k in result:
                    if k not in answers: answers[k] = {}
                    answers[k][model] = result[k]
            except Exception as e: raise
        for x in d:
            if x['id'] in answers: x['answers'] = answers[x['id']]
        print_json(d, config.answer_output)
    except asyncio.CancelledError: pass
    except RetryError: pass
    finally: await SessionManager.close()