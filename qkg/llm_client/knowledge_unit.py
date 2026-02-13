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


class Structurize(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, KNOWLEDGE_SCHEMA)
        return text['mechanism_units']

    def _organize_inputs(self, inputs):
        return [{'role': 'system', 'content': KNOWLEDGE}, {'role': 'user', 'content': inputs}], {}


class KnowledgeFilter(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        try:
            jsonschema.validate(text, KNOWLEDGE_FILTER_SCHEMA)
        except jsonschema.ValidationError:
            print(response, text)
            raise
        
        return text["atomicity"] == 'atomic' and \
               text['explicit_invariant_presence'] != 'none' and \
               text['structural_perturbability'] == 'yes' and \
               text['hidden_dependency_risk'] != "high" and \
               text['counterfactual_coherence'] == "high" and \
               text['reasoning_depth_potential'] == "high" and \
               text["minimal_example_quality"]["concreteness"] != "low" and \
               text["minimal_example_quality"]["operational_evaluability"] != "no" and \
               text["minimal_example_quality"]["perturbation_anchor_strength"] == "strong"
    
    def _organize_inputs(self, inputs):
        inputs = json.dumps(inputs, indent=2)
        return [{'role': 'system', 'content': KNOWLEDGE_FILTER}, {'role': 'user', 'content': inputs}], {}


class Upgrade(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, UPGRADE_SCHEMA)
        if text["upgrade_analysis"]['upgrade_applied']:
            assert text['upgrade_analysis']["original_invariant"] in context['inputs']['invariants']
        return {"upgrade": text, "origin": context['inputs']}

    def _organize_inputs(self, inputs):
        string = json.dumps(inputs, indent=2)
        return [{'role': 'system', 'content': UPGRADE}, {'role': 'user', 'content': string}], {"inputs": inputs}


class UpgradeRank(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, UPGRADE_RANK_SCHEMA)
        if text['level'] in ['L4', 'L5']:
            del context['inputs']['upgrade_analysis']
            return {**context['inputs'], "L5": text['level'] == "L5"}

    def _organize_inputs(self, inputs):
        string = json.dumps(inputs, indent=2)
        return [{'role': 'system', 'content': UPGRADE_RANK}, {'role': 'user', 'content': string}], {"inputs": inputs}
    

async def structure(content: str):
    model = Structurize(config.generate_model, GREEDY_PARAMS, 1800)
    try:
        generated = await model.call(inputs=content)
        return generated
    except Exception as e:
        print(f"StructureNode {e}")
    

async def filter_structure(generated: list[Dict[str, Any]]):
    tasks = [asyncio.create_task(KnowledgeFilter(config.critic_models[0], GREEDY_PARAMS).call(inputs=g)) for g in generated]
    kept = []
    for g, task in zip(generated, asyncio.as_completed(tasks)):
        try:
            keep = await task
            if isinstance(keep, bool) and keep: kept.append(g)
        except Exception as e:
            print(f"StructureFilterNode {e}")
    return kept
    

async def upgrade(generated: list[Dict[str, Any]]):
    tasks = [asyncio.create_task(Upgrade(config.generate_model, SAMPLE_PARAMS).call(inputs=g)) for g in generated]
    revised = []
    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            if isinstance(result, dict) and result: revised.append(result['upgrade'])
        except Exception as e:
            print(f"UpgradeNode {e}")
    return revised


async def refilter_structure(generated: list[Dict[str, Any]]):
    tasks = [asyncio.create_task(KnowledgeFilter(config.critic_models[0], GREEDY_PARAMS).call(inputs=g['upgrade'])) for g in generated]
    kept = []
    for g, task in zip(generated, asyncio.as_completed(tasks)):
        try:
            keep = await task
            if isinstance(keep, bool) and keep: kept.append(g)
            else: kept.append(g['origin'])
        except Exception as e:
            print(f"StructureFilter2Node {e}")
            kept.append(g['origin'])
    return kept


async def upgraderank(generated: Dict[str, Any]):
    tasks = [asyncio.create_task(UpgradeRank(config.critic_models[0], SAMPLE_PARAMS).call(inputs=g)) for g in generated]
    revised = []
    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            if isinstance(result, dict) and result: revised.append(result)
        except Exception as e:
            print(f"UpgradeRankNode {e}")
    return revised
