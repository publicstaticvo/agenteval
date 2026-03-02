import json, jsonschema
import asyncio
from prompts import *
from utils import extract_json
from .base import AsyncLLMClient
from .valid import Valid

SAMPLE_PARAMS = {'temperature': 0.8, "max_tokens": 8192, "top_p": 0.95}
GREEDY_PARAMS = {
    'temperature': 0.0, "max_tokens": 8192, "seed": 42, "repetition_penalty": 1.0,
    "length_penalty": 1.0, "no_repeat_ngram_size": 0,
}


class Generate(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, GENERATE_SCHEMA)
        is_correct = 0
        for x in text["reasoning_paths"]:
            if x['is_correct']: is_correct += 1
        assert is_correct == 1, is_correct
        return text
    
    def _organize_inputs(self, inputs):
        unit = json.dumps(inputs['unit'], indent=2)
        return [{'role': 'system', 'content': GENERATE}, {'role': 'user', 'content': unit}], {}


def reasoning_paths_to_list(q):
    options_with = []
    for x in q['reasoning_paths']: 
        options_with.append(f"{x['id']}:")
        for y in x['chain']: options_with.append(f"- {y}") 
        options_with.append(f"- Conclusion: {x['conclusion']}") 
    return options_with
    

class Filter(AsyncLLMClient):

    SCHEMA = FILTER_SCHEMA
    PROMPT = FILTER

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, self.SCHEMA)
        text["dominance_cue_detected"] = not text["dominance_cue_detected"]
        return all(x for x in text.values() if isinstance(x, bool)), text
    
    def _organize_inputs(self, inputs):   
        options_with = reasoning_paths_to_list(inputs)
        inputs = f"Question: {inputs['question']}\n\nReasoning Paths:\n{'\n'.join(options_with)}"
        prompt = [{'role': 'system', 'content': self.PROMPT}, {'role': 'user', 'content': inputs}]
        return prompt, {}
    

class MiniTester(AsyncLLMClient):

    ANSWERS = EXPAND_OPTIONS + [NOT_ANSWERABLE]

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, MINITEST_SCHEMA)
        return text['selected_option']
    
    def _organize_inputs(self, inputs):   
        options_with = reasoning_paths_to_list(inputs)
        options_with.append(f"{NOT_ANSWERABLE}: None of the above is plausible.")
        inputs = f"Question: {inputs['question']}\n\nReasoning Paths:\n{'\n'.join(options_with)}"
        prompt = [{'role': 'system', 'content': MINITEST}, {'role': 'user', 'content': inputs}]
        return prompt, {}
    

class ReverseConsistency(AsyncLLMClient):

    SCHEMA = REVERSE_CONSISTENCY_SCHEMA
    PROMPT = REVERSE_CONSISTENCY

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, self.SCHEMA)
        return all(x['constructable'] for x in text.values())
    
    def _organize_inputs(self, inputs):
        paths, options_with = [], []
        for x in inputs['reasoning_paths']:
            if not x['is_correct']: paths.append([x['chain'], x['conclusion']])  
        for k, x in zip(OPTIONS[:-1], paths): 
            options_with.append(f"{k}:")
            for y in x[0]: options_with.append(f"- {y}") 
            options_with.append(f"- Conclusion: {x[1]}")  
        string = REVERSE_CONSISTENCY_USER.format(
            q=inputs['question'],
            unit=json.dumps(inputs['mechanism_summary'], indent=2),
            options='\n'.join(options_with)
        )
        return [{'role': 'system', 'content': self.PROMPT}, {'role': 'user', 'content': string}], {}


class Rewrite(AsyncLLMClient):

    PROMPT = REVISE
    SCHEMA = REVISE_SCHEMA
    
    def _organize_inputs(self, inputs):
        inputs = json.dumps(inputs, indent=2)
        return [{'role': 'system', 'content': self.PROMPT}, {'role': 'user', 'content': inputs}], {}
    

async def generate(unit: dict):
    # unit = {k: v for k, v in unit.items() if k != 'minimal_example'}
    model = Generate(config.generate_model, SAMPLE_PARAMS)
    try:
        generated = await model.call(inputs={"unit": unit})
        if generated: return generated
    except Exception as e:
        print(f"GenerateNode {e}")


async def valid(generated: dict):    
    try:
        inputs = f"Question: {generated['question']}\n\nOptions:\n{'\n'.join(reasoning_paths_to_list(generated))}"
        keep, text = await Valid(config.critic_models[0], GREEDY_PARAMS).call(inputs=inputs)
    except Exception as e:
        return f"ValidInGen {e}"
    if not keep: 
        generated['reason'] = text
        return "Not Valid"
    
    try:
        keep, text = await Filter(config.critic_models[0], GREEDY_PARAMS).call(inputs=generated)
    except Exception as e:
        return f"Filter {e}"
    if not keep: 
        generated['reason'] = text
        return "Not Filter"

    tasks = [asyncio.create_task(MiniTester(c, GREEDY_PARAMS).call(inputs=generated)) for c in config.critic_models]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for x in generated['reasoning_paths']:
        if x['is_correct']: correct_answer = x['id']
    keys = OPTIONS + [NOT_ANSWERABLE]
    count = {k: 0 for k in keys}
    for r in results:
        if r in keys: count[r] += 1
        else: count[NOT_ANSWERABLE] += 1
    if count[NOT_ANSWERABLE]: return NOT_ANSWERABLE
    del count[NOT_ANSWERABLE]
    if count[correct_answer] == 3: return "3 correct answer"
    generated['model_results'] = count
    max_value = max(count.values())
    if max_value == 3: return "All select False"
    elif max_value == 2 and count[correct_answer] < 2: return "Majority select False"
    if count[correct_answer] == 0: return "No correct answer"
    
    try:
        keep = await ReverseConsistency(config.critic_models[0], GREEDY_PARAMS).call(inputs=generated)
    except Exception as e:
        return f"ReverseConsistency {e}"
    if not keep: return "Not ReverseConsistency"

    return "Passed"
    

async def rewrite(generated: list[dict]):
    tasks = [asyncio.create_task(Rewrite(config.generate_model, SAMPLE_PARAMS).call(inputs=g)) for g in generated]
    refine = []
    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            if result: refine.append(result)
        except Exception as e:
            print(f"RewriteNode {e}")
    return refine


async def generateloop(generated: list[dict]):
    pass
