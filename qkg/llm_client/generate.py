import json, jsonschema
import asyncio
from prompts import *
from utils import extract_json
from .base import AsyncLLMClient

SAMPLE_PARAMS = {'temperature': 0.8, "max_tokens": 8192, "top_p": 0.95}


class Generate(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, GENERATE_SCHEMA)
        text['id'] = context['id']
        return text
    
    def _organize_inputs(self, inputs):
        unit = json.dumps(inputs['unit'], indent=2)
        return [{'role': 'system', 'content': GENERATE}, {'role': 'user', 'content': unit}], {'id': inputs['id']}    


async def generateloop(unit: list[dict]):
    async def _generate_with_new_sc(tp, sc, qid):
        model = Generate(config.generate_model, SAMPLE_PARAMS)
        try:
            inputs = {"target_proposition": tp, 'structural_commitments': sc}
            generated = await model.call(inputs={"unit": inputs, 'id': qid})
            if generated: return generated
        except Exception as e:
            print(f"GenerateNode in {qid}: {e}")

    tasks, questions = [], []
    tp = unit["target_proposition"]
    for i, x in enumerate(unit['structural_commitments']):        
        # removal
        new_sc = [y['statement'] for y in unit['structural_commitments'] if y['id'] != x['id']]
        tasks.append(asyncio.create_task(_generate_with_new_sc(tp, new_sc, f"{unit['id']}{x['id']}R")))
        # isolation
        tasks.append(asyncio.create_task(_generate_with_new_sc(tp, [x['statement']], f"{unit['id']}{x['id']}S")))
        if 'perturbs' in x:
            # weakening
            new_sc = [y['statement'] for y in unit['structural_commitments']]
            new_sc[i] = x['perturbs'][0]["statement"]
            tasks.append(asyncio.create_task(_generate_with_new_sc(tp, new_sc, f"{unit['id']}{x['id']}M")))
            # inversion
            new_sc = [y['statement'] for y in unit['structural_commitments']]
            new_sc[i] = x['perturbs'][1]["statement"]
            tasks.append(asyncio.create_task(_generate_with_new_sc(tp, new_sc, f"{unit['id']}{x['id']}I")))
    
    for task in tasks:
        q = await task
        if q: questions.append(q)
    
    return questions