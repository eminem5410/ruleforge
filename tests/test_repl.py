import json
from unittest.mock import patch

from ruleforge.repl import RuleForgeREPL


def run_command(repl, line):
    """Execute one REPL command simulating the cmdloop (precmd -> onecmd)."""
    with patch("builtins.print") as mocked_print:
        processed_line = repl.precmd(line)
        if processed_line:
            repl.onecmd(processed_line)
    return "\n".join(
        " ".join(str(arg) for arg in call.args)
        for call in mocked_print.call_args_list
    )


def test_context_auto_infers_schema():
    repl = RuleForgeREPL()

    output = run_command(
        repl,
        '.context {"customer": {"age": 25}}',
    )

    assert repl.context == {"customer": {"age": 25}}
    assert repl.schema is None
    assert repl.engine.schema == {
        "customer": {
            "age": "Integer"
        }
    }
    assert "Schema: auto-inferred" in output


def test_explicit_schema_reinitializes_engine():
    repl = RuleForgeREPL()

    output = run_command(
        repl,
        '.schema {"customer": {"age": "Integer"}}',
    )

    assert repl.schema == {
        "customer": {
            "age": "Integer"
        }
    }
    assert repl.engine.schema == repl.schema
    assert "explicit" in output


def test_multiline_rule_allow():
    repl = RuleForgeREPL()

    run_command(
        repl,
        '.context {"customer": {"age": 25}}',
    )

    repl.precmd("RULE adult LANGUAGE 1")
    repl.precmd("WHEN customer.age >= 18")
    repl.precmd("THEN ALLOW")

    with patch("builtins.print") as mocked_print:
        command = repl.precmd("END")
        if command:
            repl.onecmd(command)

    output = "\n".join(
        " ".join(str(arg) for arg in call.args)
        for call in mocked_print.call_args_list
    )

    assert "✓ MATCH" in output
    assert "Actions: ALLOW" in output
    assert repl._in_rule is False
    assert repl.prompt == "rf> "


def test_multiline_rule_else_deny():
    repl = RuleForgeREPL()

    run_command(
        repl,
        '.schema {"customer": {"age": "Integer"}}',
    )
    run_command(
        repl,
        '.context {"customer": {"age": 15}}',
    )

    repl.precmd("RULE adult LANGUAGE 1")
    repl.precmd("WHEN customer.age >= 18")
    repl.precmd("THEN ALLOW")
    
    with patch("builtins.print") as mocked_print:
        command = repl.precmd('ELSE DENY "Minor"')
        assert command == "" # Debe permanecer en modo multilínea

        command = repl.precmd("END")
        if command:
            repl.onecmd(command)

    output = "\n".join(
        " ".join(str(arg) for arg in call.args)
        for call in mocked_print.call_args_list
    )

    assert "✗ NO MATCH" in output
    assert "Actions: DENY" in output
    assert "Minor" in output


def test_inline_rule():
    repl = RuleForgeREPL()

    run_command(
        repl,
        '.context {"customer": {"age": 25}}',
    )

    command = repl.precmd(
        'RULE adult LANGUAGE 1 WHEN customer.age >= 18 THEN ALLOW END'
    )

    assert command.startswith("eval_rule ")

    with patch("builtins.print") as mocked_print:
        repl.onecmd(command)

    output = "\n".join(
        " ".join(str(arg) for arg in call.args)
        for call in mocked_print.call_args_list
    )

    assert "✓ MATCH" in output
    assert "Actions: ALLOW" in output


def test_trace_toggle():
    repl = RuleForgeREPL()

    assert repl.trace is False

    run_command(repl, ".trace on")
    assert repl.trace is True

    run_command(repl, ".trace off")
    assert repl.trace is False


def test_empty_context_is_rejected():
    repl = RuleForgeREPL()

    output = run_command(
        repl,
        "RULE test LANGUAGE 1 WHEN true THEN ALLOW END",
    )

    assert "Context is empty" in output


def test_exit_returns_true():
    repl = RuleForgeREPL()

    with patch("builtins.print"):
        result = repl.do_exit("")

    assert result is True
