import re
import os
import sys
import glob
import json
import pandas
import inspect
from typing import get_type_hints
sys.path.append("P:\\AI4S\\agenteval\\prev_projects\\SciToolAgent-tools\\")
from tool_name_dict import CHEMICAL_TOOLS_DICT
from parse_cactus import CactusToolParser
from parse_chemtoolbench import parse_chemistry_tools, read_tool_list


def parse_chemcrow():
    csv = pandas.read_csv("P:\\AI4S\\agenteval\\tool_discription\\chemcrow.csv")
    all_tools = [{"name": f"chemcrow/{name}", "description": description, "inputs": inputs, "outputs": outputs} 
                  for name, description, inputs, outputs in \
                  zip(csv['name'], csv['description'], csv['inputs'], csv['outputs'])]
    return all_tools


def parse_sciToolEval():
    all_tools = []
    for name in CHEMICAL_TOOLS_DICT:
        tool_docstring = CHEMICAL_TOOLS_DICT[name].__doc__

        try:
            inputs_idx = tool_docstring.index('Args:')
            outputs_idx = tool_docstring.index('Returns:')
            text = tool_docstring[:inputs_idx].strip()
            inputs = tool_docstring[inputs_idx + 5:outputs_idx].strip()
            outputs = tool_docstring[outputs_idx + 8:].strip()            

        except ValueError:
            sig = inspect.signature(CHEMICAL_TOOLS_DICT[name])                
            inputs = ""
            for param_name, param in sig.parameters.items():
                if param.annotation != inspect.Parameter.empty:
                    # Get the name of the type
                    type_name = getattr(param.annotation, '__name__', str(param.annotation))
                    inputs += f"{param_name} ({type_name})"
                else:
                    inputs += f"{param_name}"
                if param.default != inspect.Parameter.empty:
                    inputs += f"\tDefault: {param.default}"
                inputs += "\n"
            inputs = inputs.strip()
            # Get return type name
            outputs = ""
            if sig.return_annotation != inspect.Signature.empty:
                outputs = getattr(sig.return_annotation, '__name__', str(sig.return_annotation))

        name = f"scitooleval/{name}"
        all_tools.append({"name": name, "description": text.strip(), "inputs": inputs, "outputs": outputs})
    
    return all_tools


def parse_chemToolBench():
    base_path = "P:\\AI4S\\agenteval\\prev_projects\\ChemistryAgent-tools"
    all_tools = []
    for lib in ['chemlib', 'chemistrytools']:
        _, tools_paths = read_tool_list(base_path, lib)
        for n in tools_paths:
            with open(os.path.join(base_path, lib, n), encoding='utf-8') as f: code = f.read()
            tools = parse_chemistry_tools(code)
            for tool in tools: tool['name'] = f"{lib}/{tool['name']}"
            all_tools.extend(tools)

    return all_tools


def parse_cactus():
    parser = CactusToolParser()
    all_tools = []
    for f in glob.glob("P:\\AI4S\\agenteval\\prev_projects\\cactus-tools\\*.py"):
        if "__init__" in f: continue
        tools = parser.parse_file(f)
        for tool in tools: tool['name'] = f"cactus/{tool['name']}"
        all_tools.extend(tools)

    return all_tools

if __name__ == "__main__":
    all_tools = parse_cactus() + parse_chemcrow() + parse_chemToolBench() + parse_sciToolEval()
    with open("P:\\AI4S\\agenteval\\tools.txt", "w+", encoding="utf-8") as f:
        for i, csv in enumerate(all_tools):
            if isinstance(csv['inputs'], list): print(csv)
            csv['inputs'] = "\t".join(csv['inputs'].split("\n"))
            f.write(f"""{i}
Name: {csv['name']}
Description: {csv['description']}
Inputs: 
\t{csv['inputs']}
Outputs:
\t{csv['outputs']}
""")
    with open("P:\\AI4S\\agenteval\\tools.jsonl", "w+", encoding="utf-8") as f:
        for x in all_tools:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")