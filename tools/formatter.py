import json

def infer_type(val):
    if isinstance(val, bool): return "Boolean"
    if isinstance(val, int): return "Integer"
    if isinstance(val, float): return "Decimal"
    if isinstance(val, str): return "String"
    if isinstance(val, dict): return infer_schema(val)
    if isinstance(val, list): return f"Array<{infer_type(val[0]) if val else 'Unknown'}>"
    return "Unknown"

def infer_schema(obj):
    if not isinstance(obj, dict): return {}
    return {k: infer_type(v) for k, v in obj.items()}

def format_context(context, schema):
    if schema is None:
        return "✓ Context loaded\n  Schema: auto-inferred"
    return "✓ Context loaded\n  Schema: explicit"

def format_decision(decision):
    status = "✓ MATCH" if decision.matched else "✗ NO MATCH"
    actions_str = ", ".join(f"{a.action_type}" + (f" \"{a.value}\"" if a.value and a.value != 'None' else "") for a in decision.actions)
    return f"{status}\n  Rule: {decision.rule_id}\n  Actions: {actions_str}"

def format_trace_node(node, indent=1):
    if not node or not isinstance(node, dict):
        return ""
    
    sp = "  " * indent
    node_type = node.get("NodeType", "Unknown")
    val = node.get("Value")
    op = node.get("Operator")
    short_circ = node.get("ShortCircuited", False)
    
    # Formatear valor para que sea legible (strings y arrays usan JSON)
    if isinstance(val, str):
        val_str = f'"{val}"' if not val.startswith('"') else val
    elif isinstance(val, (list, dict)):
        val_str = json.dumps(val)
    else:
        val_str = str(val)
        
    label = node_type
    if op:
        label += f" {op}"
        
    if short_circ:
        line = f"{sp}{label} -> [Short-Circuited]"
    else:
        line = f"{sp}{label} -> {val_str}"
        
    children = node.get("Children", [])
    children_str = ""
    if children:
        children_str = "\n" + "\n".join(filter(None, [format_trace_node(c, indent+1) for c in children]))
        
    return line + children_str

def format_trace(trace_entry):
    if not trace_entry:
        return "  (No trace available)"
        
    header = f"TRACE\n{'─' * 30}\nRule: {trace_entry.rule_name}\n"
    node_str = format_trace_node(trace_entry.evaluation_trace, indent=1)
    
    result = "  ✓ Condition matched" if trace_entry.matched else "  ✗ Condition not matched"
    actions_str = ", ".join(trace_entry.actions)
    decision_status = "✓ MATCH" if trace_entry.matched else "✗ NO MATCH"
    
    footer = f"\nRESULT\n{result}\n\nDECISION\n  {decision_status}\n  Actions: {actions_str}\n{'─' * 30}"
    return header + "\n" + node_str + footer

def format_error(error):
    err_str = str(error)
    parts = err_str.split(":", 1)
    code = parts[0] if len(parts) > 0 else "ERROR"
    msg = parts[1].strip() if len(parts) > 1 else err_str
    return f"✗ Evaluation Error\n\n  {code}:\n  {msg}\n\n  Hint: check rule syntax or schema."
