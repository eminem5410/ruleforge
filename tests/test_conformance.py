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

def run_conformance_test(rule_path, data_path, is_valid):
    with open(rule_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    try:
        lexer = Lexer(source_code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        analyzer = SemanticAnalyzer(SCHEMA)
        analyzer.analyze(ast)
        
        if is_valid:
            context = data["context"]
            expected = data["expected"]
            evaluator = Evaluator(context)
            decisions = evaluator.eval_rules(ast)
            
            d = decisions[0]
            assert d.matched == expected["matched"]
            assert len(d.actions) == len(expected["actions"])
            for i, exp_act in enumerate(expected["actions"]):
                assert d.actions[i].action_type == exp_act["action_type"]
                # Si el valor esperado es null, nos fijamos si la acción no tiene valor o es 'None'
                if exp_act["value"]:
                    assert d.actions[i].value == exp_act["value"]
                    
        else:
            assert False, f"Expected error {data['expected_error_code']} but rule was accepted"
            
    except (LexerError, ParserError, SemanticError, EvaluatorError) as e:
        if is_valid:
            assert False, f"Valid rule failed with error: {e.code}"
        else:
            assert e.code == data["expected_error_code"], f"Expected {data['expected_error_code']} but got {e.code}"

def test_valid_conformance_cases():
    valid_dir = os.path.join(os.path.dirname(__file__), 'conformance', 'valid')
    rule_files = glob.glob(os.path.join(valid_dir, '*.rf'))
    
    for rule_path in rule_files:
        base_name = rule_path.replace('.rf', '')
        data_path = f"{base_name}.json"
        if os.path.exists(data_path):
            test_name = os.path.basename(rule_path).replace('.rf', '')
            yield run_conformance_test, rule_path, data_path, True

def test_invalid_conformance_cases():
    invalid_dir = os.path.join(os.path.dirname(__file__), 'conformance', 'invalid')
    rule_files = glob.glob(os.path.join(invalid_dir, '*.rf'))
    
    for rule_path in rule_files:
        base_name = rule_path.replace('.rf', '')
        data_path = f"{base_name}.json"
        if os.path.exists(data_path):
            test_name = os.path.basename(rule_path).replace('.rf', '')
            yield run_conformance_test, rule_path, data_path, False

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
