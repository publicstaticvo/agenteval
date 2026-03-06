import json, jsonschema
import asyncio
from prompts import *
from utils import extract_json
from .base import AsyncLLMClient

SAMPLE_PARAMS = {'temperature': 0.8, "max_tokens": 8192, "top_p": 0.95}
GREEDY_PARAMS = {
    'temperature': 0.0, "max_tokens": 8192, "seed": 42, "repetition_penalty": 1.0,
    "length_penalty": 1.0, "no_repeat_ngram_size": 0,
}


class Generate(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, GENERATE_SCHEMA)
        text['id'] = context['id']
        return text
    
    def _organize_inputs(self, inputs):
        unit = json.dumps(inputs['unit'], indent=2)
        return [{'role': 'system', 'content': GENERATE}, {'role': 'user', 'content': unit}], {'id': inputs['id']} 


class Filter(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, FILTER_SCHEMA)
        return text['issues']
    
    def _organize_inputs(self, inputs):
        unit = json.dumps({'target_proposition': inputs['tp'], **inputs['q']}, indent=2)
        return [{'role': 'system', 'content': FILTER}, {'role': 'user', 'content': unit}], {}   


async def generateloop(unit: list[dict]):

    async def _generate_new_sc(tp, sc, qid):
        model = Generate(config.generate_model, SAMPLE_PARAMS)
        try:
            inputs = {"target_proposition": tp, 'structural_commitments': sc}
            generated = await model.call(inputs={"unit": inputs, 'id': qid})
            if not generated: return
        except Exception as e:
            print(f"GenerateNode in {qid}: {e}")
            return
        
        model = Filter(config.critic_models[0], GREEDY_PARAMS)
        try:
            keep = await model.call(inputs={"q": generated, 'tp': tp})
            return {"status": keep, **generated}
        except Exception as e:
            print(f"FilterNode in {qid}: {e}")

    tasks, questions = [], []
    tp = unit["target_proposition"]
    sc = [y['statement'] for y in unit['structural_commitments']]
    for i, x in enumerate(unit['structural_commitments']):  
        if 'perturbs' not in x: continue
        # removal
        new_sc = [y['statement'] for y in unit['structural_commitments'] if y['id'] != x['id']]
        tasks.append(asyncio.create_task(_generate_new_sc(tp, new_sc, f"{unit['id']}{x['id']}R")))
        # isolation
        tasks.append(asyncio.create_task(_generate_new_sc(tp, [x['statement']], f"{unit['id']}{x['id']}S")))
        # weakening
        new_sc = [y['statement'] for y in unit['structural_commitments']]
        new_sc[i] = x['perturbs'][0]["statement"]
        tasks.append(asyncio.create_task(_generate_new_sc(tp, new_sc, f"{unit['id']}{x['id']}M")))
        # inversion
        new_sc = [y['statement'] for y in unit['structural_commitments']]
        new_sc[i] = x['perturbs'][1]["statement"]
        tasks.append(asyncio.create_task(_generate_new_sc(tp, new_sc, f"{unit['id']}{x['id']}I")))
    if tasks: tasks.append(asyncio.create_task(_generate_new_sc(tp, sc, unit['id'])))
    
    for task in tasks:
        q = await task
        if q: questions.append(q)
    
    return questions