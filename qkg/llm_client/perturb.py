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

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        level = context['level']
        jsonschema.validate(text, PERTURB_SCHEMA(level))
        return text['perturbations']

    def _organize_inputs(self, inputs):
        level = inputs['level']
        unit = json.dumps(inputs['unit'], indent=2)
        system = PERTURB.format(
            subject=config.subject, 
            requirements=PERTURB_REQUIREMENTS[level], 
            level=level + 1, 
            number=PERTURB_NUMBERS[level]
        )
        return [{'role': 'system', 'content': system}, {'role': 'user', 'content': unit}], inputs


class PerturbFilter(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        try:
            jsonschema.validate(text, PERTURB_CHECK_SCHEMA(context['unit']['level']))
        except jsonschema.ValidationError:
            assert (explanations_idx := response.rfind("\"explanation\"")) >= 0
            response = response[:explanations_idx]
            assert (explanations_idx := response.rfind(",")) >= 0
            response = f"{response[:explanations_idx]}\n}}```"
            text = extract_json(response)
            jsonschema.validate(text, PERTURB_CHECK_SCHEMA(context['unit']['level']))
        l = int(context['unit']['level'][1]) - 1
        return text["level_validity"] and text["structural_validity"] and (l == 0 or text["non_trivial"]) and \
               text["plausible"] and text["internal_consistency"] and not text["hidden_failure_detected"] and \
               (text["scientific_value"] == "high" or l == 0 or (l < 3 and text["scientific_value"] != "low"))
    
    def _organize_inputs(self, inputs):
        level = int(inputs['unit']['level'][1]) - 1
        system = PERTURB_CHECK.format(
            subject=config.subject, 
            description=PERTURB_CHECK_DESCRIPTIONS[level], 
            level=inputs['unit']['level']
        )
        unit = PERTURB_CHECK_USER.format(
            unit=json.dumps(inputs['unit'], indent=2),
            origin=json.dumps(inputs['origin'], indent=2)
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


async def perturbcheck(generated: Dict[str, Any], origin: Dict[str, Any]):
    model = PerturbFilter(config.critic_models[0], GREEDY_PARAMS)
    try:
        keep = await model.call(inputs={"unit": generated, "origin": origin})
        if keep: return generated
    except Exception as e:
        raise
        print(f"PerturbCheckNode {e}")
