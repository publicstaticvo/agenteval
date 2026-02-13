import json, jsonschema
import asyncio
from tenacity import RetryError
from prompts import *
from config import LLMServerInfo
from utils import extract_json
from .base import AsyncLLMClient

GREEDY_PARAMS = {
    'temperature': 0.0, "max_tokens": 8192, "seed": 42,
    "repetition_penalty": 1.0,  # 设置为1，禁用重复惩罚
    "length_penalty": 1.0,      # 设置为1，禁用长度惩罚
    "no_repeat_ngram_size": 0,  # 设置为0，禁用n-gram重复惩罚
}


class Filter(AsyncLLMClient):

    KEY = 'eliminate'
    PROMPT = FILTER
    OPTIONS = EXPAND_OPTIONS

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        try:
            result = text[self.KEY]
        except KeyError:
            print(response, text)
            raise
        if isinstance(result, str):
            if result.lower() == "true": result = True
            elif result.lower() == "false": result = False
        return result
    
    def _organize_inputs(self, inputs):
        question = f"Question: {inputs['question']}" if 'question' in inputs else ""
        options = f"Options:{''.join(f'\n{k}. {inputs['options'][k]}' for k in self.OPTIONS if k in inputs['options'])}" if 'options' in inputs else ""
        if question and options: string = f"{question}\n\n{options}"
        else: string = question or options
        return [{'role': 'system', 'content': self.PROMPT}, {'role': 'user', 'content': string}], {}
    

class SelfContradictFilter(Filter):
    PROMPT = SELF_CONTRADICT
    KEY = "self_contradictory"


class RedundantFilter(Filter):
    PROMPT = REDUNDANT
    KEY = "contains_redundant_information"


class ImplausibleFilter(Filter):
    PROMPT = IMPLAUSIBLE
    KEY = "physically_implausible"


class JointOptionFilter(Filter):
    PROMPT = OPTION_CHECK
    
    def _availability(self, response: str, context: dict):
        response = extract_json(response)
        jsonschema.validate(response, OPTION_SCHEMA)
        return response


class Tester(AsyncLLMClient):

    OPTIONS = EXPAND_OPTIONS + [NOT_ANSWERABLE]
    PROMPT = TEST

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, TEST_SCHEMA)
        return text['selected_answer']
    
    def _organize_inputs(self, inputs):
        assert len(inputs['options']) == len(EXPAND_OPTIONS), inputs
        options = {**inputs['options'], NOT_ANSWERABLE: "None of the above. / The question is not answerable."}
        inputs = f"Question: {inputs['question']}\n\nOptions:{''.join(f'\n{k}. {options[k]}' for k in self.OPTIONS)}"
        prompt = [{'role': 'system', 'content': self.PROMPT}, {'role': 'user', 'content': inputs}]
        return prompt, {}
    

async def filter_specific(generated: list[dict[str, any]]):
    tasks = [asyncio.create_task(Filter(config.support_model, GREEDY_PARAMS).call(inputs=g, max_tokens=512)) for g in generated]
    questions = []
    for g, task in zip(generated, asyncio.as_completed(tasks)):
        try:
            eliminate = await task
            if isinstance(eliminate, bool) and not eliminate: questions.append(g)
        except Exception as e:
            print(f"FilterNode {e}")
    return questions
    

async def valid_check(generated: dict[str, any]):
    async def valid(critic: LLMServerInfo):
        try:
            self_contradict = await SelfContradictFilter(critic, GREEDY_PARAMS).call(inputs={"question": generated['question']})
        except RetryError as e:
            print(f"self_contradict {e.last_attempt}")
            self_contradict = False
        if self_contradict: return {"drop": True, "reason": "self-contradicted"}
        
        try:
            redundant = await RedundantFilter(critic, GREEDY_PARAMS).call(inputs=generated)
        except RetryError as e:
            print(f"redundant {e.last_attempt}")
            redundant = False
        if redundant: return {"drop": True, "reason": "redundant"}
        
        try:
            implausible = await ImplausibleFilter(critic, GREEDY_PARAMS).call(inputs={"question": generated['question']})
        except RetryError as e:
            print(f"implausible {e.last_attempt}")
            implausible = False
        if implausible == True: return {"drop": True, "reason": "implausible"}
        
        try:
            option_check = await JointOptionFilter(critic, GREEDY_PARAMS).call(inputs=generated)
            if option_check["trivially_true_without_question"]:
                return {"drop": True, "reason": "correct without question"}
            does_not_depend = set(option_check["trivially_false_without_question"] + option_check["does_not_depend_on_question"])
            if len(does_not_depend) >= 2:
                return {"drop": True, "reason": "too many independent"}
            redundant_options = set()
            for x in option_check["redundant_options"]: redundant_options.update(x)
        except RetryError as e:
            print(f"joint option filter {e.last_attempt}")
            return {"drop": True, "reason": "joint option filter error"}
        
        # The final check
        try:
            answer = await Tester(critic, GREEDY_PARAMS).call(inputs=generated)
            if answer == NOT_ANSWERABLE:
                return {"answer": answer, "drop": True, "reason": "Not answerable"}
            if answer in does_not_depend:
                return {"answer": answer, "drop": True, "reason": "select independent answer"}
            if answer in redundant_options:
                return {"answer": answer, "drop": True, "reason": "multiple correct answers"}
        except RetryError as e:
            print(f"tester {e.last_attempt}")
            answer = "Error"
        return {"answer": answer, "drop": False, "independent": list(does_not_depend)}
    
    # 多模型评价并试做
    tasks = [asyncio.create_task(valid(c)) for c in config.critic_models]
    answers = {}
    for c, task in zip(config.critic_models, asyncio.as_completed(tasks)):
        try:
            result = await task
            answers[c.model] = result
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"CriticNode {e}")
    return {"query": generated, "answers": answers} 
