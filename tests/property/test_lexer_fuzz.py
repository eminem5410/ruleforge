"""V11.4 Block 3.1: Lexer fuzzing.

Invariant: for any arbitrary string input, the lexer either:
  - produces a valid token list ending with EOF, or
  - raises LexerError (RF1001)

The lexer MUST NEVER throw an uncontrolled Python exception.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from ruleforge.lexer import Lexer, TokenType, LexerError


def assert_valid_tokens(tokens):
    assert isinstance(tokens, list)
    assert len(tokens) >= 1
    assert tokens[-1].type == TokenType.EOF
    for t in tokens:
        assert hasattr(t, 'type')
        assert hasattr(t, 'value')
        assert hasattr(t, 'line')
        assert hasattr(t, 'column')
        assert isinstance(t.line, int) and t.line >= 1
        assert isinstance(t.column, int) and t.column >= 1


@given(st.text())
@settings(max_examples=2000, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
def test_lexer_fuzz_arbitrary(source):
    """Arbitrary Unicode text: no uncontrolled crashes."""
    try:
        tokens = Lexer(source).tokenize()
        assert_valid_tokens(tokens)
    except LexerError:
        pass
    except Exception as exc:
        pytest.fail(f"Uncontrolled: {type(exc).__name__}: {exc}\ninput={source!r}")


HOSTILE_CHARS = st.sampled_from([
    "\x00", "\n", "\r", "\t", '"', "\\", "!", "@", "#", "$", "%", "^",
    "&", "*", "(", ")", "[", "]", "{", "}", ".", ",", ";", ":",
    "/", "+", "-", "=", "<", ">",
    "0", "1", "9", "a", "Z", "_", " ",
])

HOSTILE_FRAGMENTS = st.sampled_from([
    "//", "==", "!=", ">=", "<=",
    "true", "false", "RULE", "WHEN", "THEN", "END",
    "123abc", "1.2.3", '"unterminated', "\\x", "\\n", "\\",
    "2026-09-30", "customer.age",
])


@st.composite
def hostile_source(draw):
    parts = draw(st.lists(
        st.one_of(HOSTILE_CHARS, HOSTILE_FRAGMENTS),
        min_size=0, max_size=40,
    ))
    return "".join(parts)


@given(hostile_source())
@settings(max_examples=2000, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
def test_lexer_fuzz_hostile(source):
    """Hostile chars + fragments: no uncontrolled crashes."""
    try:
        tokens = Lexer(source).tokenize()
        assert_valid_tokens(tokens)
    except LexerError:
        pass
    except Exception as exc:
        pytest.fail(f"Uncontrolled (hostile): {type(exc).__name__}: {exc}\ninput={source!r}")


@st.composite
def long_source(draw):
    length = draw(st.integers(min_value=512, max_value=4096))
    alphabet = st.sampled_from(["a", "b", "0", "1", '"', "\\", " ", "\n", ".", "+", "-", "/", "="])
    return "".join(draw(st.lists(alphabet, min_size=length, max_size=length)))


@given(long_source())
@settings(max_examples=300, deadline=None,
          suppress_health_check=[HealthCheck.too_slow])
def test_lexer_fuzz_long_strings(source):
    """Long inputs (512-4096 chars): no crashes or hangs."""
    try:
        tokens = Lexer(source).tokenize()
        assert_valid_tokens(tokens)
    except LexerError:
        pass
    except Exception as exc:
        pytest.fail(f"Uncontrolled (long): {type(exc).__name__}: {exc}\nlength={len(source)}")
