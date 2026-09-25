import subprocess
import os
import json
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI_PATH = os.path.join(ROOT, "cli.py")

def run_cli(args):
    cmd = ["python3", CLI_PATH] + args
    return subprocess.run(cmd, capture_output=True, text=True)

def test_cli_eval_json():
    rule = os.path.join(ROOT, "examples", "erp_rules.rf")
    data = os.path.join(ROOT, "examples", "context_fail.json")
    schema = os.path.join(ROOT, "examples", "schema.json")
    
    res = run_cli(["eval", rule, data, schema, "--json"])
    assert res.returncode == 0
    output = json.loads(res.stdout)
    assert "decisions" in output
    assert len(output["decisions"]) == 2
    assert output["decisions"][0]["rule_id"] == "adult_check"
    assert output["decisions"][0]["matched"] == False

def test_cli_missing_file():
    res = run_cli(["eval", "no.rf", "no.json", "no.schema.json"])
    assert res.returncode == 2

def test_cli_rule_error_json():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".rf", delete=False) as f:
        f.write('RULE r LANGUAGE 1 WHEN customer.age > "18" THEN ALLOW END')
        temp_rule = f.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{}')
        temp_data = f.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write('{"customer": {"age": "Integer"}}')
        temp_schema = f.name

    res = run_cli(["eval", temp_rule, temp_data, temp_schema, "--json"])
    assert res.returncode == 1
    output = json.loads(res.stdout)
    assert "error" in output
    assert output["error"]["code"] == "RF3001"
    
    os.remove(temp_rule)
    os.remove(temp_data)
    os.remove(temp_schema)
