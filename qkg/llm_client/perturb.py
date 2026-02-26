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


def amendvalidate(response: str, schema: Dict[str, Any]):
    text = extract_json(response)
    try:
        jsonschema.validate(text, schema)
    except jsonschema.ValidationError:
        assert (explanations_idx := response.rfind("\"explanation\"")) >= 0
        response = response[:explanations_idx]
        assert (explanations_idx := response.rfind(",")) >= 0
        response = f"{response[:explanations_idx]}\n}}```"
        text = extract_json(response)
        jsonschema.validate(text, schema)
    return text


class Perturb(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        origin = context['unit']
        jsonschema.validate(text, PERTURB_SCHEMA(context['level']))
        returns = []
        for y in text['perturbations']:
            if 'modified_requires' not in y: y['modified_requires'] = []
            new_requires = [x['new'] for x in y['modified_requires']]
            assert len(new_requires) == len(set(new_requires))
            assert len(y['modified_requires']) + len(y['preserved_requires']) == len(origin['requires'])
            for x in y['preserved_requires']: assert x in origin['requires']
            for x in y['modified_requires']:
                assert x['new'] not in origin['requires']
                assert x['origin'] in origin['requires'] and x['origin'] not in y['preserved_requires']

            if 'modified_invariants' not in y: y['modified_invariants'] = []
            new_invariants = [x['new'] for x in y['modified_invariants']]
            assert len(new_invariants) == len(set(new_invariants))
            assert len(y['modified_invariants']) + len(y['preserved_invariants']) == len(origin['invariants'])
            for x in y['preserved_invariants']: assert x in origin['invariants']
            for x in y['modified_invariants']:
                assert x['new'] not in origin['invariants']
                assert x['origin'] in origin['invariants'] and x['origin'] not in y['preserved_invariants']

            new_mechanism = {
                "mechanism_unit": origin['mechanism_unit'],
                "requires": origin['requires'] + new_requires,
                "invariants": origin['invariants'] + new_invariants,
                "produces": y['new_produces'],
                "failure_modes": y['new_failure_modes'],
                "minimal_example": y['minimal_example']
            }
            returns.append({"new": new_mechanism, "perturb": y})
        return returns

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

    PROMPT: str = PERTURB_VALIDITY
    SCHEMA: Dict[str, Any] = PERTURB_VALIDITY_SCHEMA

    def _availability(self, response: str, context: dict):
        text = amendvalidate(response, self.SCHEMA)
        return all(x for x in text.values() if isinstance(x, bool))
    
    def _organize_inputs(self, inputs):
        unit = PERTURB_CHECK_USER.format(
            unit=json.dumps(inputs['unit'], indent=2),
            origin=json.dumps(inputs['origin'], indent=2)
        )
        return [{'role': 'system', 'content': self.PROMPT}, {'role': 'user', 'content': unit}], {}


class PerturbEqualCheck(PerturbFilter):
    PROMPT = PERTURB_DEGENERATION
    SCHEMA = PERTURB_DEGENERATION_SCHEMA


class PerturbSemanticCheck(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        assert text['level_semantic_validity'] in ['accept', 'reject']
        return text['level_semantic_validity'] == 'accept'
    
    def _organize_inputs(self, inputs):
        level = int(inputs['unit']['level'][1]) - 1
        system = PERTURB_SEMANTIC.format(subject=config.subject, description=PERTURB_SEMANTIC_CHECK[level])
        unit = PERTURB_CHECK_USER.format(
            unit=json.dumps(inputs['unit'], indent=2),
            origin=json.dumps(inputs['origin'], indent=2)
        )
        return [{'role': 'system', 'content': system}, {'role': 'user', 'content': unit}], inputs


class PerturbCritic(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        try:
            jsonschema.validate(text, PERTURB_CRITIC_SCHEMA)
        except jsonschema.ValidationError:
            print(text, response)
            raise
        level = int(context['unit']['level'][1]) - 1
        return text["final_verdict"] == "accept" and text["level_disruption_match"] == "valid" and \
               text["generates_new_problem"] and not text["degeneracy_detected"] and \
               text["scientific_tension_introduced"] != "low" and \
               (level == 0 or text["solution_reuse_status"] == "new_framework_required" or \
                (level < 3 and text["solution_reuse_status"] == "minor_modification")) and \
               (level == 0 or text["reasoning_shift"] == "structural" or \
                (level < 3 and text["reasoning_shift"] == "minor"))
    
    def _organize_inputs(self, inputs):
        level = int(inputs['unit']['level'][1]) - 1
        system = PERTURB_CRITIC.format(
            subject=config.subject, 
            level_description=PERTURB_CRITIC_DESCRIPTION[level],
            level=inputs['unit']['level'],
            mini_description=PERTURB_CRITIC_MINI_DESCRIPTION[level]
        )
        unit = PERTURB_CHECK_USER.format(
            unit=json.dumps(inputs['unit'], indent=2),
            origin=json.dumps(inputs['origin'], indent=2)
        )
        return [{'role': 'system', 'content': system}, {'role': 'user', 'content': unit}], inputs
    

async def perturb(generated: Dict[str, Any]):
    model = Perturb(config.generate_model, SAMPLE_PARAMS)
    tasks = [asyncio.create_task(model.call(inputs={"unit": generated, "level": i})) for i in range(3)]
    get = []
    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            if result: get.extend(result)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"PerturbNode {e}")
            raise
    return get


async def perturbcheck(generated: Dict[str, Any], origin: Dict[str, Any]):
    inputs = {"unit": generated["perturb"], "origin": origin}
    try:
        keep = await PerturbFilter(config.critic_models[0], GREEDY_PARAMS).call(inputs=inputs)
        if not keep: return
    except Exception as e:
        print(f"PerturbCheckNode {e}")
        return
    
    try:
        keep = await PerturbEqualCheck(config.critic_models[0], GREEDY_PARAMS).call(inputs=inputs)
        if not keep: 
            if generated['perturb']['level'] == "L1": generated['perturb']['degenerated_l1'] = True
            else: return
    except Exception as e:
        if generated['perturb']['level'] != "L1": 
            print(f"PerturbEqualCheckNode {e}")
            return
    
    try:
        keep = await PerturbSemanticCheck(config.critic_models[0], GREEDY_PARAMS).call(inputs=inputs)
        if not keep: return
    except Exception as e:
        print(f"PerturbSemanticCheckNode {e}")
        return
    
    try:
        keep = await PerturbCritic(config.critic_models[0], GREEDY_PARAMS).call(inputs=inputs)
        if not keep: return
    except Exception as e:
        print(f"PerturbCriticNode {e}")
        return
    
    return generated
