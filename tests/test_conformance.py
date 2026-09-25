import sys
import os
import json
import glob
import pytest
from ruleforge.lexer import Lexer, LexerError
from ruleforge.parser import Parser, ParserError
from ruleforge.semantic import SemanticAnalyzer, SemanticError
from ruleforge.evaluator import Evaluator, EvaluatorError

SCHEMA = {
    "customer": {"age": "Integer", "name": "String", "active": "Boolean", "email": "String"}
}

def get_cases(folder):
    base_dir = os.path.join(os.path.dirname(__file__), 'conformance', folder)
    rule_files = glob.glob(os.path.join(base_dir, '*.rf'))
    cases = []
    for rule_path in rule_files:
        data_path = rule_path.replace('.rf', '.json')
        if os.path.exists(data_path):
            cases.append((rule_path, data_path))
    return cases

valid_cases = get_cases('valid')
invalid_cases = get_cases('invalid')

@pytest.mark.parametrize("rule_path, data_path", valid_cases)
def test_valid_conformance(rule_path, data_path):
    with open(rule_path, 'r', encoding='utf-8') as f: source_code = f.read()
    with open(data_path, 'r', encoding='utf-8') as f: data = json.load(f)

    tokens = Lexer(source_code).tokenize()
    ast = Parser(tokens).parse()
    SemanticAnalyzer(SCHEMA).analyze(ast)
    
    evaluator = Evaluator(data["context"])
    decisions = evaluator.eval_rules(ast)
    
    d = decisions[0]
    expected = data["expected"]
    
    assert d.matched == expected["matched"]
    assert len(d.actions) == len(expected["actions"])
    for i, exp_act in enumerate(expected["actions"]):
        assert d.actions[i].action_type == exp_act["action_type"]
        if exp_act["value"]:
            assert d.actions[i].value == exp_act["value"]

@pytest.mark.parametrize("rule_path, data_path", invalid_cases)
def test_invalid_conformance(rule_path, data_path):
    with open(rule_path, 'r', encoding='utf-8') as f: source_code = f.read()
    with open(data_path, 'r', encoding='utf-8') as f: data = json.load(f)

    with pytest.raises((LexerError, ParserError, SemanticError, EvaluatorError)) as exc:
        tokens = Lexer(source_code).tokenize()
        ast = Parser(tokens).parse()
        SemanticAnalyzer(SCHEMA).analyze(ast)
        
    assert exc.value.code == data["expected_error_code"], f"Expected {data['expected_error_code']} but got {exc.value.code}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
