import json, jsonschema
import asyncio
from typing import Dict, Any
from prompts import *
from utils import extract_json
from .base import AsyncLLMClient

SAMPLE_PARAMS = {'temperature': 0.8, "max_tokens": 8192, "top_p": 0.95}
GREEDY_PARAMS = {
    'temperature': 0.0, "max_tokens": 8192, "seed": 42, "repetition_penalty": 1.0,
    "length_penalty": 1.0, "no_repeat_ngram_size": 0,
}


class Perturb(AsyncLLMClient):

    def _l1_availability(self, response, unit):
        for x in response:
            assert set(x["preserved_requires"]) == set(unit['requires'])  
            assert set(x["preserved_invariants"]) == set(unit['invariants'])

    def _l2_availability(self, response, unit):
        for x in response:
            assert set(x["preserved_requires"]).issubset(set(unit['requires']))
            assert len(x["modified_requires"]) + len(x["preserved_requires"]) == len(unit['requires'])
            assert set(x["preserved_invariants"]) == set(unit['invariants'])
            for y in x["modified_requires"]: assert y not in unit['requires']

    def _l3_availability(self, response, unit):
        for x in response:
            assert set(x["preserved_requires"]) == set(unit['requires'])
            assert set(x["preserved_invariants"]) == set(unit['invariants'])  
            for y in x["modified_failure_modes"]: assert y not in unit['failure_modes']

    def _l4_availability(self, response, unit):
        for x in response:
            assert set(x["preserved_requires"]) == set(unit['requires'])
            assert set(x["preserved_invariants"]).issubset(set(unit['invariants']))
            assert len(x["modified_invariants"]) + len(x["preserved_invariants"]) == len(unit['invariants'])
            for y in x["modified_invariants"]: assert y not in unit['invariants']

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        level = context['level']
        jsonschema.validate(text, PERTURB_SCHEMA(level))
        # match level:
        #     case 0: self._l1_availability(response, context['unit'])
        #     case 1: self._l2_availability(response, context['unit'])
        #     case 2: self._l3_availability(response, context['unit'])
        #     case 3 | 4: self._l4_availability(response, context['unit'])
        return text['perturbations']

    def _organize_inputs(self, inputs):
        level = inputs['level']
        unit = json.dumps(inputs['unit'], indent=2)
        system = PERTURB.format(
            subject=config.subject, 
            requirements=PERTURB_DETAILS[level], 
            level=level + 1, 
            number=PERTURB_NUMBERS[level]
        )
        return [{'role': 'system', 'content': system}, {'role': 'user', 'content': unit}], inputs
    

async def perturb(generated: Dict[str, Any]):
    model = Perturb(config.generate_model, SAMPLE_PARAMS)
    ulvl = 5 if generated['L5'] else 4
    tasks = [asyncio.create_task(model.call(inputs={"unit": generated, "level": i})) for i in range(ulvl)]
    get = []
    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            if result: get.extend(result)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"PerturbNode {e}")
    return get