"""Backlog #94 — the AI auto-review has never run.

`_auto_review()` in `app/api/routes.py` calls `async_session_factory()` with
**no binding in scope**. The file's convention is a *local* import, and two
other sites follow it correctly (`routes.py:318` inside `_open()`, and
`routes.py:1160`). The auto-review site did not, so every invocation raised
`NameError`.

It is fired with `asyncio.create_task(...)` and wrapped in
`except Exception: logger.debug(...)`, so the failure was invisible at normal
log levels. Introduced 2026-05-20 (`4a1ccce1`, "Phase T AI trade review
complete") and silently dead until 2026-10-22, when `ruff` F821 surfaced it
during unrelated work.

This file does not merely pin the one site. It walks the module with `ast` and
asserts that **every** function using `async_session_factory` has it bound —
in itself, an enclosing function, or at module level. A fourth site making the
same mistake fails this test instead of failing silently for five months.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

ROUTES = pathlib.Path(__file__).resolve().parents[1] / "app" / "api" / "routes.py"
NAME = "async_session_factory"


def _tree():
    return ast.parse(ROUTES.read_text(), filename=str(ROUTES))


_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)


def _scope_nodes(node):
    """Nodes in THIS scope only — never descending into a nested scope.

    `ast.walk` would descend, and that produced a false negative on the first
    version of this test: `_auto_review` and `_open` are siblings inside the
    same endpoint, `_open` imports the name correctly, and walking the shared
    parent therefore "found" a binding that does not exist in
    `_auto_review`'s scope. A sibling's import binds nothing here.
    """
    stack = list(ast.iter_child_nodes(node))
    while stack:
        cur = stack.pop()
        yield cur
        if not isinstance(cur, _SCOPES):
            stack.extend(ast.iter_child_nodes(cur))


def _binds(node) -> bool:
    """Does this scope bind NAME via an import or assignment?"""
    for child in _scope_nodes(node):
        if isinstance(child, ast.ImportFrom):
            if any(a.asname == NAME or a.name == NAME for a in child.names):
                return True
        if isinstance(child, ast.Import):
            if any((a.asname or a.name).split(".")[0] == NAME for a in child.names):
                return True
        if isinstance(child, ast.Assign):
            for t in child.targets:
                if isinstance(t, ast.Name) and t.id == NAME:
                    return True
    return False


def _functions_using_name():
    """(function node, chain of enclosing function nodes) for each user of NAME."""
    tree = _tree()
    out = []

    def walk(node, chain):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Scope-LOCAL, for the same reason `_binds` is: `ast.walk`
                # descends into nested functions, so the endpoint enclosing
                # `_auto_review` was reported as an offender for a name only
                # its closures use. A false positive mirroring the false
                # negative that the first version of `_binds` produced.
                uses = any(
                    isinstance(n, ast.Name) and n.id == NAME
                    and isinstance(n.ctx, ast.Load)
                    for n in _scope_nodes(child)
                )
                if uses:
                    out.append((child, list(chain)))
                walk(child, chain + [child])
            else:
                walk(child, chain)

    walk(tree, [])
    return out


class TestEverySessionFactoryUserHasItBound:

    def test_the_name_is_used_somewhere(self):
        """Guard the guard: if the name disappears this test must not pass
        vacuously."""
        assert _functions_using_name(), (
            f"no function in routes.py uses {NAME} — this test has gone "
            f"vacuous and should be deleted or retargeted"
        )

    def test_no_function_uses_the_session_factory_unbound(self):
        tree = _tree()
        module_binds = any(
            isinstance(n, ast.ImportFrom)
            and any(a.asname == NAME or a.name == NAME for a in n.names)
            for n in tree.body
        )

        offenders = []
        for fn, chain in _functions_using_name():
            if module_binds or _binds(fn) or any(_binds(p) for p in chain):
                continue
            offenders.append(f"{fn.name} (line {fn.lineno})")

        assert offenders == [], (
            f"{offenders} call {NAME}() with no binding in scope — every call "
            f"raises NameError. routes.py imports it LOCALLY (see :318 and "
            f":1160), so each user needs its own import."
        )


class TestTheFailureIsVisible:
    """The NameError was swallowed at DEBUG for five months. A background task
    that discards its exception needs a level somebody reads."""

    def test_the_auto_review_handler_does_not_log_at_debug(self):
        src = ROUTES.read_text()
        start = src.index("async def _auto_review()")
        end = src.index("create_task(_auto_review())", start)
        block = src[start:end]
        # A CALL, not the bare name: the fix's own comment mentions
        # `logger.debug` to explain the history, and a substring search on the
        # name made this test fail against correct code.
        code = "\n".join(ln for ln in block.splitlines()
                         if not ln.lstrip().startswith("#"))
        assert "logger.debug(" not in code, (
            "auto_review swallows its exception at DEBUG, which is why #94 "
            "went unnoticed for five months"
        )
        assert any(f"{lvl}(" in code for lvl in
                   ("logger.warning", "logger.error", "logger.exception"))
