import os
import ast
import sys
import json
from typing import List, Dict, Any


def read_tool_list(base_path, project_name):
    with open(os.path.join(base_path, project_name, "tools.json"), encoding='utf-8') as f:
        tools = json.load(f)
    tools_set = set(tools[k]['path'] for k in tools)
    return tools, tools_set

    
def parse_chemistry_tools(python_code: str) -> List[Dict]:
    """
    Parse chemistry tool functions from Python code and extract their metadata.
    
    Parameters:
        python_code: str, Python source code containing function definitions
        
    Returns:
        tools: list[dict], list of parsed tool information
    """
    tools = []
    
    # Parse the Python code into an AST
    tree = ast.parse(python_code)
    
    # Iterate through all function definitions
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            tool_info = parse_function_node(node)
            if tool_info:
                tools.append(tool_info)
    
    return tools


def parse_function_node(func_node: ast.FunctionDef) -> Dict:
    """
    Parse a single function node and extract its metadata.
    
    Parameters:
        func_node: ast.FunctionDef, the function node to parse
        
    Returns:
        tool_info: dict, parsed tool information
    """
    # Get the docstring
    docstring = ast.get_docstring(func_node)
    if not docstring:
        return None
    
    # Parse docstring to extract structured information
    doc_parts = parse_docstring(docstring)
    
    # Get function name
    function_name = func_node.name
    
    # Parse parameters from function signature
    parameters = []
    for arg in func_node.args.args:
        param_name = arg.arg
        param_type = ast.unparse(arg.annotation) if arg.annotation else None
        parameters.append({
            'name': param_name,
            'type': param_type
        })
    parameters = "\n".join([f"{x['name']} ({x['type']})" for x in parameters])
    
    # Parse return type from function signature
    return_type = ast.unparse(func_node.returns) if func_node.returns else None
    
    # Build the tool info dictionary
    tool_info = {
        'name': function_name,
        'description': doc_parts.get('description', ''),
        'inputs': doc_parts.get('parameters', parameters),
        'outputs': doc_parts.get('returns', return_type)
    }
    
    return tool_info


def parse_docstring(docstring: str) -> Dict:
    """
    Parse a docstring to extract Name, Description, Parameters, and Returns sections.
    
    Parameters:
        docstring: str, the function's docstring
        
    Returns:
        doc_parts: dict, parsed sections of the docstring
    """
    lines = docstring.strip().split('\n')
    doc_parts = {}
    current_section = None
    parameters = []
    
    for line in lines:
        line = line.strip()
        
        if line.startswith('Name:'):
            current_section = 'name'
            doc_parts['name'] = line.replace('Name:', '').strip()
        elif line.startswith('Description:'):
            current_section = 'description'
            doc_parts['description'] = line.replace('Description:', '').strip()
        elif line.startswith('Parameters:'):
            current_section = 'parameters'
        elif line.startswith('Returns:'):
            current_section = 'returns'
        elif current_section == 'parameters' and line and ':' in line:
            parameters.append(line.strip())
        elif current_section == 'returns' and line and ':' in line:
            doc_parts['returns'] = line.strip()
    
    if parameters:
        doc_parts['parameters'] = "\n".join(parameters)
    
    return doc_parts


if __name__ == "__main__":
    base_path = "P:\\AI4S\\agenteval\\prev_projects\\ChemistryAgent-tools"
    lib = sys.argv[1]
    tools_dict, tools_paths = read_tool_list(base_path, lib)
    print(len(tools_dict))
    all_tools = []
    for n in tools_paths:
        with open(os.path.join(base_path, lib, n), encoding='utf-8') as f:
            code = f.read()
        all_tools.extend(parse_chemistry_tools(code))
    for tool in all_tools:
        tool['name'] = f"{sys.argv[1]}/{tool['name']}"
    print("Extracted Tools:")
    all_tools = sorted(all_tools, key=lambda x: x['name'])
    print(json.dumps(all_tools, indent=2), len(all_tools))