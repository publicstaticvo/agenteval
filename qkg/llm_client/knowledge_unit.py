import json, jsonschema
import networkx as nx
import asyncio
from typing import Dict, Any
from prompts import *
from utils import extract_json, skeleton_to_text
from .base import AsyncLLMClient
from session_manager import file_lock

SAMPLE_PARAMS = {'temperature': 0.8, "max_tokens": 8192, "top_p": 0.95}
GREEDY_PARAMS = {
    'temperature': 0.0, "max_tokens": 8192, "seed": 42, "repetition_penalty": 1.0,
    "length_penalty": 1.0, "no_repeat_ngram_size": 0,
}


class Mechanism(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, KNOWLEDGE_SCHEMA)
        return text

    def _organize_inputs(self, inputs):
        return [{'role': 'system', 'content': KNOWLEDGE}, {'role': 'user', 'content': inputs}], {}


class MechanismFilter(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, KNOWLEDGE_FILTER_SCHEMA)       
        return text
    
    def _organize_inputs(self, inputs):
        inputs = json.dumps({
            "paper_title": inputs['paper']['title'], 
            "paper_abstract": inputs['paper']['abstract'], 
            "mechanism_unit": inputs['unit']
        }, indent=2)
        return [{'role': 'system', 'content': KNOWLEDGE_FILTER}, {'role': 'user', 'content': inputs}], {}


async def structloop(paper):
    if "mechanism" in paper: del paper['mechanism']
    content = skeleton_to_text(paper['structure'])      

    model = Mechanism(config.generate_model, GREEDY_PARAMS, 1800)
    try:
        generated = await model.call(inputs=content)
    except Exception as e:
        return f"StructureNode {e}"
    if not generated: return "No mechanism"

    async with file_lock:
        with open(config.temp_output, 'a+', encoding='utf-8') as f:
            f.write(json.dumps({**generated, "id": paper['id']}) + "\n")

    model = MechanismFilter(config.critic_models[0], GREEDY_PARAMS, 1800)
    try:
        keep = await model.call(inputs={"unit": generated, "paper": paper})
        print(list(len(x) for x in keep.values()))
        if any(keep.values()): 
            if keep['target_proposition_issues']: decision = "Fail target proposition"
            else:
                issued_commitment = set(x['id'] for x in keep['structural_commitment_issues'])
                if (rest := len(generated['structural_commitments']) - len(issued_commitment)) > 0:
                    decision = f"Passed after reduce to {rest} SCs"
                else: decision = f"Failed no valid structural commitment"
        else:
            decision = "Passed Perfect"
    except Exception as e:
        decision = keep = f"StructureFilterNode {e}"        

    paper['mechanism'] = {"decision": decision, "status": keep, **generated}
    return paper
