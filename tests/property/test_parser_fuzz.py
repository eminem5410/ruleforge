from hypothesis import given, settings, strategies as st, HealthCheck

from ruleforge.lexer import Lexer, LexerError
from ruleforge.parser import Parser, ParserError


def parse_source(source: str):
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse()


# ------------------------------------------------------------
# Property 1 — cualquier fuente arbitraria
# ------------------------------------------------------------

@given(st.text())
@settings(
    max_examples=2000,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_parser_fuzz_arbitrary(source):
    try:
        parse_source(source)
    except (LexerError, ParserError):
        pass
    except Exception as exc:
        raise AssertionError(
            f"Uncontrolled parser exception: "
            f"{type(exc).__name__}: {exc!s:.300}"
        ) from exc


# ------------------------------------------------------------
# Property 2 — fragmentos hostiles orientados al parser
# ------------------------------------------------------------

HOSTILE_FRAGMENTS = [
    "",
    "RULE",
    "RULE fuzz",
    "RULE fuzz LANGUAGE",
    "RULE fuzz LANGUAGE 1",
    "RULE fuzz LANGUAGE 1 WHEN",
    "RULE fuzz LANGUAGE 1 WHEN true",
    "RULE fuzz LANGUAGE 1 WHEN true THEN",
    "RULE fuzz LANGUAGE 1 WHEN true THEN ALLOW",
    "RULE fuzz LANGUAGE 1 WHEN true THEN ALLOW ELSE",
    "RULE fuzz LANGUAGE 1 WHEN true THEN ALLOW END",
    "RULE fuzz LANGUAGE 1 WHEN (true THEN ALLOW END",
    "RULE fuzz LANGUAGE 1 WHEN true) THEN ALLOW END",
    "RULE fuzz LANGUAGE 1 WHEN NOT THEN ALLOW END",
    "RULE fuzz LANGUAGE 1 WHEN IS NULL THEN ALLOW END",
    "RULE fuzz LANGUAGE 1 WHEN customer. THEN ALLOW END",
    "RULE fuzz LANGUAGE 1 WHEN customer.age[ THEN ALLOW END",
    "RULE fuzz LANGUAGE 1 WHEN customer.age[] THEN ALLOW END",
    "RULE fuzz LANGUAGE 1 WHEN customer.age[1 THEN ALLOW END",
    "RULE fuzz LANGUAGE 1 WHEN customer.age[1][2] THEN ALLOW END",
    "RULE fuzz LANGUAGE 1 WHEN [1,2,] THEN ALLOW END",
    "RULE fuzz LANGUAGE 1 WHEN [] THEN ALLOW END",
    "RULE fuzz LANGUAGE 1 WHEN ANY customer.tags WHERE THEN ALLOW END",
    "RULE fuzz LANGUAGE 1 WHEN ALL customer.tags WHERE THEN ALLOW END",
    "RULE fuzz LANGUAGE 1 WHEN FILTER customer.tags WHERE THEN ALLOW END",
    "RULE fuzz LANGUAGE 1 WHEN MAP customer.tags USING THEN ALLOW END",
    'RULE fuzz LANGUAGE 1 WHEN DATE "2020" THEN ALLOW END',
    'RULE fuzz LANGUAGE 1 WHEN DATE "9999-99-99" THEN ALLOW END',
    'RULE fuzz LANGUAGE 1 WHEN DATE "----" THEN ALLOW END',
    'RULE fuzz LANGUAGE 1 WHEN DATE "" THEN ALLOW END',
    'RULE fuzz LANGUAGE 1 WHEN customer.age >= THEN ALLOW END',
    'RULE fuzz LANGUAGE 1 WHEN customer.age + THEN ALLOW END',
    'RULE fuzz LANGUAGE 1 WHEN customer.age / THEN ALLOW END',
    'RULE fuzz LANGUAGE 1 WHEN customer.age == THEN ALLOW END',
    'RULE fuzz LANGUAGE 1 WHEN customer.age IS NOT THEN ALLOW END',
    'RULE fuzz LANGUAGE 1 THEN ALLOW END',
    'RULE fuzz LANGUAGE 1 WHEN true THEN NO_ACTION ALLOW END',
    'RULE fuzz LANGUAGE 1 WHEN true THEN SET END',
    'RULE fuzz LANGUAGE 1 WHEN true THEN SET customer.age = END',
    'RULE fuzz LANGUAGE 1 WHEN true THEN EMIT END',
    'RULE fuzz LANGUAGE 1 WHEN true THEN EMIT "EVENT" WITH END',
    'RULE fuzz LANGUAGE 1 WHEN true THEN EMIT "EVENT" WITH customer. END',
    'RULE fuzz LANGUAGE 1 WHEN true THEN ALLOW ELSE DENY END',
]

HOSTILE_ATOMS = [
    "RULE",
    "LANGUAGE",
    "WHEN",
    "THEN",
    "ELSE",
    "END",
    "ALLOW",
    "DENY",
    "ALERT",
    "APPLY",
    "NO_ACTION",
    "EMIT",
    "SET",
    "DATE",
    "ANY",
    "ALL",
    "FILTER",
    "MAP",
    "NOT",
    "AND",
    "OR",
    "IS",
    "NULL",
    "true",
    "false",
    "0",
    "1",
    "999999",
    "(",
    ")",
    "[",
    "]",
    ".",
    ",",
    "=",
    "==",
    "!=",
    ">",
    "<",
    ">=",
    "<=",
    "+",
    "-",
    "*",
    "/",
    '"',
    '"x"',
    '"2020"',
    "customer",
    "age",
]


@st.composite
def hostile_source(draw):
    fragments = draw(
        st.lists(
            st.one_of(
                st.sampled_from(HOSTILE_FRAGMENTS),
                st.sampled_from(HOSTILE_ATOMS),
            ),
            min_size=0,
            max_size=30,
        )
    )
    return " ".join(fragments)


@given(hostile_source())
@settings(
    max_examples=2000,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_parser_fuzz_hostile(source):
    try:
        parse_source(source)
    except (LexerError, ParserError):
        pass
    except Exception as exc:
        raise AssertionError(
            f"Uncontrolled parser exception: "
            f"{type(exc).__name__}: {exc!s:.300}\n"
            f"source={source!r}"
        ) from exc


# ------------------------------------------------------------
# Property 3 — nesting / profundidad
# ------------------------------------------------------------

@st.composite
def deep_expression(draw):
    depth = draw(st.integers(min_value=1, max_value=300))
    kind = draw(st.sampled_from(["paren", "not"]))

    if kind == "paren":
        expr = "(" * depth + "true" + ")" * depth
    else:
        expr = "NOT " * depth + "true"

    return f"RULE fuzz LANGUAGE 1 WHEN {expr} THEN ALLOW END"


@given(deep_expression())
@settings(
    max_examples=300,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_parser_fuzz_deep(source):
    try:
        parse_source(source)
    except (LexerError, ParserError):
        pass
    except Exception as exc:
        raise AssertionError(
            f"Uncontrolled deep-parser exception: "
            f"{type(exc).__name__}: {exc!s:.300}\n"
            f"source length={len(source)}"
        ) from exc
