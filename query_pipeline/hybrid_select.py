from prompts import *
from utils import extract_json
from llm_client import AsyncLLMClient


class HybridSelectStep1(AsyncLLMClient):

    def _availability(self, response: str):
        candidates = extract_json(response)['candidates']
        paragraphs = self._context['paragraphs']
        for x in candidates:
            p = paragraphs[int(x['paragraph_index']) - 1]
            text = x['sentence_text']
            assert text in p, (text, p)
            candidates['evidence_pool'] = p
        return candidates
    
    def _organize_inputs(self, inputs):
        prompt = HYBRID_SELECT_STEP_1_USER.format(text=inputs['content'])
        return [{'role': 'system', 'content': HYBRID_SELECT_STEP_1},
                {'role': 'user', 'content': prompt}]


class HybridSelectStep2(AsyncLLMClient):

    def _availability(self, response: str):
        results = extract_json(response)
        if not results['reproducible']: return {}
        return {"text": self._context['input']['sentence_text'], "evidences": results['supporting_sentences']}
    
    def _organize_inputs(self, inputs):
        self._context['input'] = inputs
        prompt = HYBRID_SELECT_STEP_2_USER.format(text=inputs['sentence_text'], evidences=inputs['evidence_pool'])
        return [{'role': 'system', 'content': HYBRID_SELECT_STEP_2},
                {'role': 'user', 'content': prompt}]
    

class HybridSelectStep3(AsyncLLMClient):

    def _availability(self, response: str):
        results = extract_json(response)
        if results['method_type'].lower() != "dry": return {}
        return {
            "result": self._context['input']['sentence']['text'], 
            "method": results['method_sentences']
        }
    
    def _organize_inputs(self, inputs):
        self._context['input'] = inputs['sentence']['text']
        prompt = HYBRID_SELECT_STEP_3_USER.format(text=inputs['sentence']['text'], paper=inputs['paper'])
        return [{'role': 'system', 'content': HYBRID_SELECT_STEP_3},
                {'role': 'user', 'content': prompt}]    
