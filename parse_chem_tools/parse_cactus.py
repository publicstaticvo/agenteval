import ast
import json
from typing import List, Dict, Any


class CactusToolParser:
    """Parser for extracting tool information from Python class definitions."""
    
    def parse_file(self, filepath: str) -> List[Dict[str, str]]:
        """Parse a Python file and extract all tool definitions.
        
        Parameters
        ----------
        filepath : str
            Path to the Python file containing tool class definitions
            
        Returns
        -------
        List[Dict[str, str]]
            List of dictionaries containing tool information
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self.parse_content(content)
    
    def parse_content(self, content: str) -> List[Dict[str, str]]:
        """Parse Python code content and extract tool definitions.
        
        Parameters
        ----------
        content : str
            Python code content as string
            
        Returns
        -------
        List[Dict[str, str]]
            List of dictionaries containing tool information
        """
        tree = ast.parse(content)
        
        # First pass: extract module-level constants
        constants = self._extract_module_constants(tree)
        
        # Second pass: extract tool classes
        tools = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                tool_info = self._extract_tool_info(node, constants)
                if tool_info:
                    tools.append(tool_info)
        
        return tools
    
    
    def _extract_module_constants(self, tree: ast.Module) -> Dict[str, str]:
        """Extract module-level string constants.
        
        Parameters
        ----------
        tree : ast.Module
            AST tree of the module
            
        Returns
        -------
        Dict[str, str]
            Dictionary mapping constant names to their string values
        """
        constants = {}
        
        for node in tree.body:
            # Handle regular assignments: DESC = "..."
            if isinstance(node, ast.Assign):
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    var_name = node.targets[0].id
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        constants[var_name] = node.value.value.strip()
            
            # Handle annotated assignments: DESC: str = "..."
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and node.value:
                    var_name = node.target.id
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        constants[var_name] = node.value.value.strip()
        
        return constants
    
    def _extract_tool_info(self, class_node: ast.ClassDef, constants: Dict[str, str] = None) -> Dict[str, str]:
        """Extract tool information from a class definition node.
        
        Parameters
        ----------
        class_node : ast.ClassDef
            AST node representing a class definition
        constants : Dict[str, str], optional
            Module-level constants for variable resolution
            
        Returns
        -------
        Dict[str, str]
            Dictionary with name, description, inputs, and outputs
        """
        if constants is None:
            constants = {}
        
        tool_info = {
            "name": "",
            "description": "",
            "inputs": "",
            "outputs": ""
        }
        
        # Extract class attributes (name and description)
        for item in class_node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                attr_name = item.target.id
                
                if attr_name == "name":
                    if isinstance(item.value, ast.Constant):
                        tool_info["name"] = item.value.value
                    elif isinstance(item.value, ast.Name) and item.value.id in constants:
                        tool_info["name"] = constants[item.value.id]
                        
                elif attr_name == "description":
                    if isinstance(item.value, ast.Constant):
                        tool_info["description"] = item.value.value
                    elif isinstance(item.value, ast.Name) and item.value.id in constants:
                        tool_info["description"] = constants[item.value.id]
        
        # Find the _run method and extract inputs/outputs from docstring
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "_run":
                inputs, outputs = self._parse_docstring(ast.get_docstring(item), item)
                tool_info["inputs"] = inputs
                tool_info["outputs"] = outputs
                break
        
        # Only return if we found a valid tool (has name and description)
        if tool_info["name"] and tool_info["description"]:
            return tool_info
        
        return None
    
    def _parse_docstring(self, docstring: str, func_node: ast.FunctionDef) -> tuple:
        """Parse function docstring to extract parameters and return types.
        
        Parameters
        ----------
        docstring : str
            The docstring of the function
        func_node : ast.FunctionDef
            AST node of the function
            
        Returns
        -------
        tuple
            (inputs_str, outputs_str)
        """
        if not docstring:
            # Fall back to function signature if no docstring
            return self._extract_from_signature(func_node)
        
        lines = docstring.split('\n')
        inputs = []
        outputs = []
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # Detect sections
            if line.startswith('Parameters'):
                current_section = 'parameters'
                continue
            elif line.startswith('Returns'):
                current_section = 'returns'
                continue
            elif line.startswith('---'):
                continue
            
            # Parse content based on current section
            if current_section == 'parameters' and line and not line.startswith('-'):
                # Format: "param_name: type" or "param_name : type"
                if ':' in line:
                    inputs.append(line)
            elif current_section == 'returns' and line and not line.startswith('-'):
                outputs.append(line)
        
        inputs_str = ', '.join(inputs) if inputs else ""
        outputs_str = ' '.join(outputs) if outputs else ""
        
        return inputs_str, outputs_str
    
    def _extract_from_signature(self, func_node: ast.FunctionDef) -> tuple:
        """Extract input/output info from function signature as fallback.
        
        Parameters
        ----------
        func_node : ast.FunctionDef
            AST node of the function
            
        Returns
        -------
        tuple
            (inputs_str, outputs_str)
        """
        inputs = []
        
        # Extract parameters (skip 'self')
        for arg in func_node.args.args:
            if arg.arg != 'self':
                if arg.annotation:
                    inputs.append(f"{arg.arg}: {ast.unparse(arg.annotation)}")
                else:
                    inputs.append(arg.arg)
        
        # Extract return type
        outputs = ""
        if func_node.returns:
            outputs = ast.unparse(func_node.returns)
        
        return ', '.join(inputs), outputs


if __name__ == "__main__":
    import glob

    parser = CactusToolParser()
    all_tools = []
    for f in glob.glob("P:\\AI4S\\agenteval\\prev_projects\\cactus-tools\\*.py"):
        if "__init__" in f: continue
        tools = parser.parse_file(f)
        for tool in tools: tool['name'] = f"cactus/{tool['name']}"
        all_tools.extend(tools)

    print("Extracted Tools:")
    all_tools = sorted(all_tools, key=lambda x: x['name'])
    print(json.dumps(all_tools, indent=2), len(all_tools))