import json, jsonschema
import asyncio
import random
import math
from tenacity import RetryError
from prompts import *
from config import LLMServerInfo
from utils import extract_json
from .base import AsyncLLMClient

GREEDY_PARAMS = {
    'temperature': 0.0, "max_tokens": 8192, "seed": 42, "repetition_penalty": 1.0,
    "length_penalty": 1.0, "no_repeat_ngram_size": 0,
}


def to_string_question(inputs, add_not_answerable=True):
    options = [(inputs['correct_option']['statement'], "C")] + [(x['statement'], f"W{i}") for i, x in enumerate(inputs['wrong_options'])]
    random.shuffle(options)
    options_with, omap = {}, []
    for o, (x, i) in zip(EXPAND_OPTIONS, options):
        options_with[o] = x
        omap.append(i)
    if add_not_answerable:
        options = {**options_with, NOT_ANSWERABLE: "None of the above. / The question is not answerable."}
        valid_answers = EXPAND_OPTIONS + [NOT_ANSWERABLE]
    else:
        options = options_with
        valid_answers = EXPAND_OPTIONS
    inputs = f"Question: {inputs['question']}\n\nOptions:{''.join(f'\n{k}. {options[k]}' for k in valid_answers)}"
    return inputs, omap


class Valid(AsyncLLMClient):

    SCHEMA = VALID_SCHEMA
    PROMPT = VALID

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, self.SCHEMA)
        return all(x['decision'] for x in text.values()), text
    
    def _organize_inputs(self, inputs):
        return [{'role': 'system', 'content': self.PROMPT}, {'role': 'user', 'content': inputs}], {}
    

class ValidTension(Valid):
    PROMPT = VALID_TENSION
    SCHEMA = VALID_TENSION_SCHEMA


class Tester(AsyncLLMClient):

    ANSWERS = EXPAND_OPTIONS + [NOT_ANSWERABLE]

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, TEST_SCHEMA)
        if text['selected_answer'] == NOT_ANSWERABLE: answer = "Not answerable"
        else: answer = context['omap'][EXPAND_OPTIONS.index(text['selected_answer'])]
        return {"answer": answer, "reason": text['reasoning_steps']}
    
    def _organize_inputs(self, inputs):
        inputs, omap = to_string_question(inputs)
        prompt = [{'role': 'system', 'content': TEST}, {'role': 'user', 'content': inputs}]
        return prompt, {"omap": omap}


class WrongPathCheck(AsyncLLMClient):
    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, WRONG_ANSWER_SCHEMA(len(context['wrong'])))
        for i, x in enumerate(text["error_analysis"]):
            x['model_id'] = context['omap'][i]
            if x["classification"] == 'execution_error': x['primary_type'] = 'execution_error'
        return text["error_analysis"]
    
    def _organize_inputs(self, inputs):
        system = WRONG_ANSWER.format(
            subject=config.subject,
            error_pattern_set=json.dumps(ERROR_PATTERN_SET, indent=2)
        )
        contents, model_to_M = [], []
        for i, m in enumerate(inputs['wrong']):
            model_to_M.append(m['model'])
            ans = inputs['q']['wrong_options'][int(m['answer'][1]) - 1]['statement']
            contents.append(f"- model: M{i + 1}\n  model_answer: {ans}\n  reasoning_steps: {m['reason']}")
        inputs['omap'] = model_to_M
        user = WRONG_ANSWER_USER.format(q=json.dumps(inputs['q'], indent=2), content='\n\n'.join(contents))
        return [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], inputs
    

class RightPathCheck(AsyncLLMClient):
    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, RIGHT_ANSWER_SCHEMA(len(context['right'])))
        for i, x in enumerate(text["analysis"]): x['model_id'] = context['omap'][i]
        return text["analysis"]
    
    def _organize_inputs(self, inputs):
        contents, model_to_M = [], []
        for i, m in inputs['right']:
            model_to_M.append(m['model'])
            ans = inputs['q']['correct_option']['statement']
            contents.append(f"- model: M{i + 1}\n  model_answer: {ans}\n  reasoning_steps: {m['reason']}")
        inputs['omap'] = model_to_M
        user = RIGHT_ANSWER_USER.format(q=json.dumps(inputs['q'], indent=2), content='\n\n'.join(contents))
        return [{'role': 'system', 'content': RIGHT_ANSWER}, {'role': 'user', 'content': user}], inputs


async def valid_check(generated: dict):
    try:
        inputs, _ = to_string_question(generated)
        keep, text = await Valid(config.critic_models[0], GREEDY_PARAMS).call(inputs=inputs)
    except Exception as e:
        print(f"Filter {e}")
        return "Filter Error"
    if not keep: return {"status": "QuestionCheck", **generated, "reason": text}
    
    try:
        keep, text = await ValidTension(config.critic_models[0], GREEDY_PARAMS).call(inputs=generated)
    except Exception as e:
        print(f"FilterTension {e}")
        return "FilterTension Error"
    if not keep: return {"status": "TensionCheck", **generated, "reason": text}

    # 多模型评价并试做
    async def _test(c: LLMServerInfo):
        try:
            answer = await Tester(c, GREEDY_PARAMS).call(inputs=generated)
            if isinstance(answer, dict) and answer:
                answer['model'] = c.model
                return answer
        except Exception as e:
            print(f"Tester {c.model} {e}")

    tasks = [asyncio.create_task(_test(c)) for c in config.critic_models]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    right, wrong, valid_answers = [], [], 0
    for s in results:
        if not isinstance(s, dict): continue
        if s['answer'] == "Not answerable": return {"status": "Not Answerable", **generated, "reason": results}
        elif s['answer'] == "C": right.append(s)
        else: wrong.append(s)
        valid_answers += 1
    if valid_answers <= 1: return "Model Answer Error"
    if len(right) == 0: return {"status": "Acc = 0", **generated, "reason": results}
    if len(wrong) == 0: return {"status": "Acc = 1", **generated, "reason": results}
    
    try:
        inputs = {"q": generated, "wrong": wrong}
        new_wrong = await WrongPathCheck(config.critic_models[0], GREEDY_PARAMS).call(inputs=inputs)
    except RetryError as e:
        print(f"WrongPathCheck {e.last_attempt}")
        return "WrongPathCheckError"
    expected_error_count = 0
    for w, nw in zip(wrong, new_wrong):
        w["error_type"] = nw["classification"]
        w['primary_type'] = nw['primary_pattern']
        expected_error = generated['wrong_options'][int(w['answer'][1]) - 1]["error_pattern"]['primary_type']
        if w['primary_type'] == expected_error: expected_error_count += 1
    if expected_error_count == 0: return "No expected error"
    
    try:
        inputs = {"q": generated, "right": right}
        new_right = await RightPathCheck(config.critic_models[0], GREEDY_PARAMS).call(inputs=inputs)
    except RetryError as e:
        print(f"RightPathCheck {e.last_attempt}")
        return "RightPathCheckError"
    structure_count = 0
    for w, nw in zip(right, new_right):
        w["type"] = nw["reasoning_type"]
        w['depth'] = nw['reasoning_depth']
        if w['type'] == 'structural_joint_reasoning': structure_count += 1
    if structure_count == 0: return "No structure reasoning"

    generated['answers'] = right + wrong
    return {"status": "Passed", **generated}
