import subprocess
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI_PATH = os.path.join(REPO_ROOT, "tools", "cli.py")
PYTHON = sys.executable # Usar el mismo intérprete que ejecuta pytest (.venv)

def run_cli(args):
    cmd = [PYTHON, CLI_PATH] + args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def test_cli_eval_match(tmp_path):
    rule_file = tmp_path / "rule.rf"
    rule_file.write_text("RULE adult LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END")
    
    context = '{"customer": {"age": 25}}'
    stdout, stderr, rc = run_cli(["eval", str(rule_file), "--context", context])
    
    assert rc == 0
    assert "✓ MATCH" in stdout
    assert "Actions: ALLOW" in stdout

def test_cli_eval_no_match(tmp_path):
    rule_file = tmp_path / "rule.rf"
    rule_file.write_text('RULE adult LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW ELSE DENY "Minor" END')
    
    context = '{"customer": {"age": 15}}'
    stdout, stderr, rc = run_cli(["eval", str(rule_file), "--context", context])
    
    assert rc == 0
    assert "✗ NO MATCH" in stdout
    assert 'DENY "Minor"' in stdout

def test_cli_eval_trace(tmp_path):
    rule_file = tmp_path / "rule.rf"
    rule_file.write_text("RULE adult LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END")
    
    context = '{"customer": {"age": 25}}'
    stdout, stderr, rc = run_cli(["eval", str(rule_file), "--context", context, "--trace"])
    
    assert rc == 0
    assert "✓ MATCH" in stdout
    assert "TRACE" in stdout
    assert "BinaryExpression >=" in stdout

def test_cli_eval_invalid_context(tmp_path):
    rule_file = tmp_path / "rule.rf"
    rule_file.write_text("RULE adult LANGUAGE 1 WHEN true THEN ALLOW END")
    
    stdout, stderr, rc = run_cli(["eval", str(rule_file), "--context", "{invalid}"])
    
    assert rc == 1
    assert "❌ Invalid context JSON" in stdout or "❌ Invalid context JSON" in stderr

def test_cli_eval_file_not_found(tmp_path):
    stdout, stderr, rc = run_cli(["eval", "nonexistent.rf", "--context", "{}"])
    
    assert rc == 1
    assert "❌ File not found" in stdout or "❌ File not found" in stderr

def test_cli_eval_multiple_rules_trace(tmp_path):
    rule_file = tmp_path / "rules.rf"
    rule_file.write_text(
        """RULE adult LANGUAGE 1
WHEN customer.age >= 18
THEN ALLOW
END

RULE minor LANGUAGE 1
WHEN customer.age < 18
THEN DENY "Minor"
END"""
    )

    context = '{"customer": {"age": 25}}'
    stdout, stderr, rc = run_cli(
        ["eval", str(rule_file), "--context", context, "--trace"]
    )

    assert rc == 0
    assert "Rule: adult" in stdout
    assert "Rule: minor" in stdout

    # Cada trace debe corresponder a su decisión.
    assert stdout.count("TRACE") == 2
    assert stdout.count("Rule: adult") >= 2
    assert stdout.count("Rule: minor") >= 1


def test_cli_eval_invalid_schema(tmp_path):
    rule_file = tmp_path / "rule.rf"
    rule_file.write_text(
        "RULE adult LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END"
    )

    context = '{"customer": {"age": 25}}'
    stdout, stderr, rc = run_cli(
        ["eval", str(rule_file), "--context", context, "--schema", "{invalid}"]
    )

    assert rc == 1
    assert "❌ Invalid schema JSON" in stdout or "❌ Invalid schema JSON" in stderr

