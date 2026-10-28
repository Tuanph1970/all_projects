"""The two schema sources, and the invariant that actually holds between them.

The Tech Debt register carried this as *"prediction-service double schema
source (SQLAlchemy + inline SQL) — Drift: change one, forget the other"*, and
CLAUDE.md says to "keep both in sync". Measured 2026-10-28, that framing is
wrong in a way worth recording:

    inline SQL in app/main.py  (9)  model_instances, solution_indicators,
                                    tbl_all_models, tbl_model_defaul_value,
                                    tbl_model_field, tbl_model_sub_types,
                                    tbl_param_option, tbl_solution,
                                    technical_indicators
    SQLAlchemy models (4)           ml_models, predictions,
                                    model_training_logs, prediction_requests

    OVERLAP: none.

They are not two definitions of one schema; they are two schemas — the legacy
WebAPI-compatible tables, which exist only as SQL string literals executed at
startup, and the new domain tables owned by `Base`. There is no table to
"keep in sync", so the drift the row warned about cannot happen.

What CAN happen, and what these tests pin instead:

1. **The sets start overlapping.** The day a table is defined in both places
   the register's warning becomes real and nothing would notice, because the
   two definitions are in different files and neither is executed by the
   other's tests. That is the invariant worth enforcing.
2. **The legacy family drifts against itself** — an `ALTER` or seed `INSERT`
   aimed at a table no `CREATE` in the same list produces. Those statements
   run in sequence at startup against a live database; a typo'd table name
   fails there and nowhere else.
3. **A query references a table nothing creates.** This is not hypothetical:
   `tbl_time_series` is selected by `/covariates` and is created by neither
   source nor anywhere else in the repo. See the last test.
"""
from __future__ import annotations

import ast
import pathlib
import re

import pytest

APP = pathlib.Path(__file__).resolve().parents[1] / "app"
MAIN = APP / "main.py"
DOMAIN = APP / "models" / "domain.py"

_CREATE = re.compile(r"CREATE TABLE(?:\s+IF NOT EXISTS)?\s+`?([A-Za-z_][A-Za-z0-9_]*)`?", re.I)
_ALTER = re.compile(r"ALTER TABLE\s+`?([A-Za-z_][A-Za-z0-9_]*)`?", re.I)
_INSERT = re.compile(r"INSERT\s+(?:IGNORE\s+)?INTO\s+`?([A-Za-z_][A-Za-z0-9_]*)`?", re.I)
_TABLENAME = re.compile(r'__tablename__\s*=\s*"([^"]+)"')


def _sql_literals(path: pathlib.Path) -> list[str]:
    """Every string constant in the module that looks like a SQL statement."""
    starts = re.compile(r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|WITH)\b", re.I)
    out = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if starts.match(node.value):
                out.append(node.value)
    return out


def inline_sql_tables() -> set[str]:
    return {t.lower() for s in _sql_literals(MAIN) for t in _CREATE.findall(s)}


def sqlalchemy_tables() -> set[str]:
    return set(_TABLENAME.findall(DOMAIN.read_text()))


# ---------------------------------------------------------------------------
# 1. The invariant the register should have carried
# ---------------------------------------------------------------------------

def test_the_two_schema_sources_define_disjoint_tables():
    """No table may be defined by BOTH `Base` and the inline SQL.

    This is the enforceable reading of CLAUDE.md's "keep both in sync": the
    only way they can disagree is if they both own something. Today they own
    nothing in common, and this test fails the moment that changes — which is
    the point, because the two definitions live in different files and neither
    file's tests execute the other.
    """
    overlap = inline_sql_tables() & sqlalchemy_tables()
    assert not overlap, (
        f"these tables are now defined TWICE — once in app/main.py's inline SQL "
        f"and once as a SQLAlchemy model: {sorted(overlap)}. Pick one owner, or "
        f"the two will drift silently.")


def test_both_sources_are_actually_populated():
    """Guards the guard: an extractor that silently returns nothing would make
    the disjointness test pass forever."""
    assert len(inline_sql_tables()) >= 9, sorted(inline_sql_tables())
    assert len(sqlalchemy_tables()) >= 4, sorted(sqlalchemy_tables())


# ---------------------------------------------------------------------------
# 2. The legacy family against itself
# ---------------------------------------------------------------------------

def test_every_altered_or_seeded_table_is_also_created():
    """`MIGRATION_SQL` and `SEED_DATA_SQL` run in sequence at startup against a
    live database. A statement naming a table that no `CREATE` in the same
    module produces fails there and nowhere else — no test, no import error,
    no type checker sees it.
    """
    created = inline_sql_tables()
    literals = _sql_literals(MAIN)
    touched = {t.lower() for s in literals for t in _ALTER.findall(s)}
    touched |= {t.lower() for s in literals for t in _INSERT.findall(s)}
    missing = sorted(touched - created)
    assert not missing, (
        f"app/main.py alters or seeds tables it never creates: {missing}. These "
        f"statements execute at startup and will fail against the database.")


# ---------------------------------------------------------------------------
# 3. The gap that is real today
# ---------------------------------------------------------------------------

#: Referenced in SQL but created by neither schema source, nor anywhere else in
#: stock_microservices/. Listed explicitly so it cannot be forgotten, and so a
#: NEW unbacked reference is distinguishable from this known one.
KNOWN_UNBACKED_TABLES = {"tbl_time_series"}

#: Owned by other services; prediction-service reads them cross-service, which
#: is expected in this monolith-migration codebase.
EXTERNALLY_OWNED_TABLES = {"portfolios", "portfolio_holdings"}


def test_tbl_time_series_is_still_unbacked_and_the_endpoint_still_degrades():
    """`/covariates` selects from `tbl_time_series`, which nothing creates.

    The call is wrapped in `except Exception -> logger.warning -> return []`,
    so the endpoint answers `[]` forever rather than erroring: the screen shows
    no covariates and only a log line says why. That is a deliberate
    degradation, and this test pins it so the mitigation cannot be removed
    while the gap remains.

    It fails — deliberately — if someone CREATES the table (then drop this
    test and the KNOWN_UNBACKED entry) or deletes the dead endpoint.
    """
    routes = (APP / "api" / "solution_routes.py").read_text()
    assert "tbl_time_series" in routes, (
        "tbl_time_series is no longer referenced — if the endpoint was removed "
        "or the table created, drop this test and its KNOWN_UNBACKED entry")
    assert "tbl_time_series" not in inline_sql_tables() | sqlalchemy_tables()

    # The guard that keeps it from 500ing, asserted on the handler itself.
    handler = routes[routes.index("async def get_predict_covariates"):]
    handler = handler[: handler.index("\n@")] if "\n@" in handler else handler
    assert "except Exception" in handler and "return []" in handler, (
        "the covariates handler no longer degrades gracefully, so a missing "
        "tbl_time_series would now surface as a 500")


@pytest.mark.parametrize("table", sorted(KNOWN_UNBACKED_TABLES))
def test_known_unbacked_tables_are_genuinely_unbacked(table):
    """Keeps the allowlist honest — an entry that IS backed should be removed."""
    assert table not in inline_sql_tables() | sqlalchemy_tables()
