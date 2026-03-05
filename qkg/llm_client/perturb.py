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


class KnowledgeClass(AsyncLLMClient):
    PROMPT = KNOWLEDGE_CLASS

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, KNOWLEDGE_CLASS_SCHEMA(context['structural_commitments']))
        for x, y in zip(context['structural_commitments'], text): x['dependency_type'] = y['dependency_type']
        return context
    
    def _organize_inputs(self, inputs):
        unit = json.dumps(inputs, indent=2)
        return [{'role': 'system', 'content': self.PROMPT}, {'role': 'user', 'content': unit}], inputs


class Perturb(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, PERTURB_SCHEMA)
        return text['perturbations'], context['id']

    def _organize_inputs(self, inputs):
        ci = inputs['structural_commitment']['id']
        inputs['structural_commitment'] = inputs['structural_commitment']['statement']
        unit = json.dumps(inputs, indent=2)
        return [{'role': 'system', 'content': PERTURB}, {'role': 'user', 'content': unit}], {"id": ci}


async def perturbloop(paper):
    generated = {
        "target_proposition": paper['mechanism']['target_proposition'],
        'structural_commitments': paper['mechanism']['structural_commitments']
    }
    try:
        generated = await KnowledgeClass(config.generate_model, SAMPLE_PARAMS).call(inputs=generated)
    except Exception as e:
        print(f"KnowledgeClass {e}")        
        return
    tasks = []
    for x in generated['structural_commitments']:
        inputs = {"target_proposition": generated['target_proposition'], 'structural_commitment': x}
        tasks.append(asyncio.create_task(Perturb(config.generate_model, SAMPLE_PARAMS).call(inputs=inputs)))
    for task in asyncio.as_completed(tasks):
        try:
            result, identifier = await task
            if result and isinstance(result, list):
                for x in generated['structural_commitments']:
                    if x['id'] == identifier:
                        x['perturbs'] = result
                        break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"PerturbNode {e}")
            continue
    paper['mechanism'] = generated  
    return paper
