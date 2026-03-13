import jsonschema
from prompts import *
from .base import AsyncLLMClient
from utils import extract_json


class Correctness(AsyncLLMClient):

    def _availability(self, response, context):
        text = extract_json(response)
        jsonschema.validate(text, CORRECTNESS_SCHEMA)
        text['id'] = context['id']
        return text

    def _organize_inputs(self, inputs):
        return [{"role": "user", "content": CORRECTNESS.format(
            question=inputs['q']['question'],
            answer=inputs['a']['answer'],
            correct_answer=inputs['q']['answer']
        )}], {"id": inputs['q']['id']}