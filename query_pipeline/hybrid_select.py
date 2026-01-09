from prompts import *
from utils import extract_json
from llm_client import AsyncLLMClient


class HybridSelectStep1(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        candidates = extract_json(response)['candidates']
        paragraphs = context['paragraphs']
        valid_candidates = []
        for x in candidates:
            p = paragraphs[int(x['paragraph_index']) - 1]
            if x['sentence_text'].lower() not in p.lower(): continue
            x['evidence_pool'] = p
            valid_candidates.append(x)
        return valid_candidates
    
    def _organize_inputs(self, inputs):
        prompt = HYBRID_SELECT_STEP_1_USER.format(text=inputs['content'])
        return [{'role': 'system', 'content': HYBRID_SELECT_STEP_1}, {'role': 'user', 'content': prompt}], {}


class HybridSelectStep2(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        results = extract_json(response)
        if not results['reproducible']: return {}
        return {"text": context['input']['sentence_text'], "evidences": results['supporting_sentences']}
    
    def _organize_inputs(self, inputs):
        prompt = HYBRID_SELECT_STEP_2_USER.format(text=inputs['sentence_text'], evidences=inputs['evidence_pool'])
        return [{'role': 'system', 'content': HYBRID_SELECT_STEP_2}, {'role': 'user', 'content': prompt}], {"input": inputs}
    

class HybridSelectStep3(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        try:
            results = extract_json(response)
            if results['method_type'].lower() != "dry": return {}
            return {"result": context['input'], "method": results['method_sentences']}
        except Exception as e:
            print(e)
    
    def _organize_inputs(self, inputs):
        prompt = HYBRID_SELECT_STEP_3_USER.format(text=inputs['sentence']['text'], paper=inputs['paper'])
        return [{'role': 'system', 'content': HYBRID_SELECT_STEP_3}, {'role': 'user', 'content': prompt}], {"input": inputs['sentence']['text']}  
