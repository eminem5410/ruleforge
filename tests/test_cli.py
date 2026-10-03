import subprocess
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Ejecutar como modulo instalable
PYTHON = sys.executable

def run_cli(args):
    cmd = [PYTHON, "-m", "ruleforge.cli"] + args
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
    assert 'Actions: DENY "Minor"' in stdout

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
    stdout, stderr, rc = run_cli(["eval", str(rule_file), "--context", context, "--trace"])
    assert rc == 0
    assert "Rule: adult" in stdout
    assert "Rule: minor" in stdout
    assert stdout.count("TRACE") == 2

def test_cli_eval_invalid_schema(tmp_path):
    rule_file = tmp_path / "rule.rf"
    rule_file.write_text("RULE adult LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END")
    context = '{"customer": {"age": 25}}'
    stdout, stderr, rc = run_cli(["eval", str(rule_file), "--context", context, "--schema", "{invalid}"])
    assert rc == 1
    assert "❌ Invalid schema JSON" in stdout or "❌ Invalid schema JSON" in stderr

# --- Tests para CHECK ---

def test_cli_check_valid_with_schema(tmp_path):
    rule_file = tmp_path / "rule.rf"
    rule_file.write_text("RULE adult LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END")
    schema = '{"customer": {"age": "Integer"}}'
    stdout, stderr, rc = run_cli(["check", str(rule_file), "--schema", schema])
    assert rc == 0
    assert "✓ Valid" in stdout
    assert "Rules: 1" in stdout
    assert "Language: 1" in stdout

def test_cli_check_valid_no_schema(tmp_path):
    rule_file = tmp_path / "rule.rf"
    rule_file.write_text("RULE fallback LANGUAGE 1 WHEN true THEN ALLOW END")
    stdout, stderr, rc = run_cli(["check", str(rule_file)])
    assert rc == 0
    assert "✓ Valid" in stdout
    assert "Rules: 1" in stdout
    assert "No schema provided" not in stdout
    assert "Semantic validation of domain properties will fail" not in stdout

def test_cli_check_invalid_syntax(tmp_path):
    rule_file = tmp_path / "rule.rf"
    rule_file.write_text("RULE adult LANGUAGE 1 WHEN customer.age >= THEN ALLOW END")
    stdout, stderr, rc = run_cli(["check", str(rule_file), "--schema", '{"customer": {"age": "Integer"}}'])
    assert rc == 1
    assert "✗ Evaluation Error" in stdout or "✗ Evaluation Error" in stderr

def test_cli_check_semantic_error(tmp_path):
    rule_file = tmp_path / "rule.rf"
    rule_file.write_text("RULE adult LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END")
    stdout, stderr, rc = run_cli(["check", str(rule_file)])
    assert rc == 1
    assert "RF3002" in stdout or "RF3002" in stderr

def test_cli_check_file_not_found(tmp_path):
    stdout, stderr, rc = run_cli(["check", "nonexistent.rf"])
    assert rc == 1
    assert "❌ File not found" in stdout or "❌ File not found" in stderr

def test_cli_check_invalid_schema(tmp_path):
    rule_file = tmp_path / "rule.rf"
    rule_file.write_text("RULE adult LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END")
    stdout, stderr, rc = run_cli(["check", str(rule_file), "--schema", "{invalid}"])
    assert rc == 1
    assert "❌ Invalid schema JSON" in stdout or "❌ Invalid schema JSON" in stderr

# --- Tests para TRACE ---

def test_cli_trace_match(tmp_path):
    rule_file = tmp_path / "rule.rf"
    rule_file.write_text("RULE adult LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END")
    context = '{"customer": {"age": 25}}'
    stdout, stderr, rc = run_cli(["trace", str(rule_file), "--context", context])
    assert rc == 0
    assert "TRACE" in stdout
    assert "Rule: adult" in stdout
    assert "✓ Condition matched" in stdout
    assert "Actions: ALLOW" in stdout

def test_cli_trace_no_match(tmp_path):
    rule_file = tmp_path / "rule.rf"
    rule_file.write_text('RULE adult LANGUAGE 1 WHEN customer.age >= 18 THEN DENY "Minor" END')
    context = '{"customer": {"age": 15}}'
    stdout, stderr, rc = run_cli(["trace", str(rule_file), "--context", context])
    assert rc == 0
    assert "TRACE" in stdout
    assert "✗ Condition not matched" in stdout
    assert "Actions: NO_ACTION" in stdout

def test_cli_trace_multiple_rules(tmp_path):
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
    stdout, stderr, rc = run_cli(["trace", str(rule_file), "--context", context])
    assert rc == 0
    assert stdout.count("TRACE") == 2
    assert "Rule: adult" in stdout
    assert "Rule: minor" in stdout

def test_cli_trace_set_pipeline(tmp_path):
    rule_file = tmp_path / "rules.rf"
    rule_file.write_text(
        """RULE add_tag LANGUAGE 1
WHEN customer.age >= 18
THEN SET customer.tags = ["adult", "vip"]
END

RULE check_tags LANGUAGE 1
WHEN LENGTH(customer.tags) == 2
THEN ALLOW
END"""
    )
    context = '{"customer": {"age": 25, "tags": ["a"]}}'
    stdout, stderr, rc = run_cli(["trace", str(rule_file), "--context", context])
    assert rc == 0
    assert "Applied Patches: customer.tags" in stdout
    assert stdout.count("TRACE") == 2

def test_cli_trace_invalid_context(tmp_path):
    rule_file = tmp_path / "rule.rf"
    rule_file.write_text("RULE adult LANGUAGE 1 WHEN true THEN ALLOW END")
    stdout, stderr, rc = run_cli(["trace", str(rule_file), "--context", "{invalid}"])
    assert rc == 1
    assert "❌ Invalid context JSON" in stdout or "❌ Invalid context JSON" in stderr

def test_cli_trace_file_not_found(tmp_path):
    stdout, stderr, rc = run_cli(["trace", "nonexistent.rf", "--context", "{}"])
    assert rc == 1
    assert "❌ File not found" in stdout or "❌ File not found" in stderr

def test_cli_trace_semantic_error(tmp_path):
    rule_file = tmp_path / "rule.rf"
    rule_file.write_text("RULE adult LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END")
    stdout, stderr, rc = run_cli(["trace", str(rule_file), "--context", "{}"])
    assert rc == 1
    assert "RF3002" in stdout or "RF3002" in stderr
