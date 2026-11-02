"""The two schema sources, and the invariant that actually holds between them.

The Tech Debt register carried this as *"prediction-service double schema
source (SQLAlchemy + inline SQL) — Drift: change one, forget the other"*, and
CLAUDE.md says to "keep both in sync". Measured 2026-10-28, that framing is
wrong in a way worth recording:

    inline SQL in app/main.py  (7)  model_instances, solution_indicators,
                                    tbl_model_defaul_value, tbl_model_field,
                                    tbl_param_option, tbl_solution,
                                    technical_indicators
                                    (was 9; tbl_all_models and
                                    tbl_model_sub_types removed under #103 —
                                    empty, created-but-never-read)
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
3. **A query references a table nothing creates.** This was not hypothetical:
   `tbl_time_series` was selected by `/covariates` and created by neither
   source nor anywhere else. Removed under Backlog #102 on 2026-10-29; the
   last two tests keep the gap from reopening, in that instance and in
   general.
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
    # Was >= 9. Backlog #103 removed tbl_all_models and tbl_model_sub_types
    # (empty, unreferenced), so the legacy family is seven. This is a floor
    # against a broken extractor, not a count of the schema.
    assert len(inline_sql_tables()) >= 7, sorted(inline_sql_tables())
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
# 3. The gap that WAS real, and is now removed (Backlog #102)
# ---------------------------------------------------------------------------
#
# `tbl_time_series` was SELECTed by `GET /solutions/covariates` and created by
# neither schema source nor anywhere else, so the handler's
# `except -> return []` answered an empty list forever. The owner settled it on
# 2026-10-29: time series are not used, and models take only technical
# indicators, which have their own live path (IndicatorSelector in
# SolutionModal -> solution_indicators -> technical_indicators, 54 rows
# seeded).
#
# Three independent confirmations that the feature was dead on BOTH sides
# before it was removed:
#   * the table did not exist in the live database (7 legacy tbl_* tables did);
#   * `tbl_solution` has no `target`, `past_covariate` or `future_covariate`
#     columns, so the read side resolved to `undefined`;
#   * `create_solution` never persisted those fields either.
#
# Removing it also fixed a live crash: `formSubmit` opened with
# `selectedPastCovariateIds.map(Number)` on a value that was `undefined` for an
# existing solution, so Save on the edit screen threw before sending anything.

def test_the_dead_covariates_endpoint_stays_removed():
    """A table nothing creates must not acquire a new caller.

    The previous version of this test asserted the endpoint still existed and
    still degraded gracefully; it failed the moment the endpoint was deleted,
    which is what it was written to do. This is its replacement: the same gap
    cannot reopen quietly.
    """
    routes = (APP / "api" / "solution_routes.py").read_text()
    assert "async def get_predict_covariates" not in routes, (
        "the /covariates handler is back — it SELECTs tbl_time_series, which "
        "nothing creates, so it can only ever return []")
    # The explanatory comment may name the table; no executable SQL may.
    sql = " ".join(_sql_literals(APP / "api" / "solution_routes.py"))
    assert "tbl_time_series" not in sql, (
        "a SQL statement references tbl_time_series again")


def test_no_table_is_queried_that_neither_source_creates():
    """The general form of the #102 defect, not just the one instance.

    Only tables this service owns are checked. `portfolios` and
    `portfolio_holdings` belong to portfolio-service and are read
    cross-service, which is expected in this monolith-migration codebase.
    """
    known = inline_sql_tables() | sqlalchemy_tables() | EXTERNALLY_OWNED_TABLES
    queried = set()
    for path in sorted(APP.rglob("**/*.py")):
        for literal in _sql_literals(path):
            for name in re.findall(
                    r"\bFROM\s+`?([a-z_][a-z0-9_]*)`?", literal, re.I):
                name = name.lower()
                # Only names shaped like this service's tables; SQL literals
                # also contain prose in docstrings ("DELETE a solution ...").
                if name in known or name.startswith(("tbl_", "model_", "solution_",
                                                     "technical_", "prediction")):
                    queried.add(name)
    unbacked = sorted(queried - known)
    assert not unbacked, (
        f"queried but created by neither schema source: {unbacked}. That is the "
        f"#102 failure mode: the query is wrapped in a try/except, so it returns "
        f"empty forever and only a log line says why.")


#: Owned by other services; prediction-service reads them cross-service.
EXTERNALLY_OWNED_TABLES = {"portfolios", "portfolio_holdings"}


# ---------------------------------------------------------------------------
# 4. Backlog #103 — the dead pair is gone, and its removal cannot destroy data
# ---------------------------------------------------------------------------

DEAD_PAIR = ("tbl_all_models", "tbl_model_sub_types")


@pytest.mark.parametrize("table", DEAD_PAIR)
def test_the_dead_model_tables_are_no_longer_created(table):
    """Backlog #103. Both were created by WEBAPI_TABLES_SQL, held 0 rows, and
    were read by nothing — tbl_all_models appeared only in its own CREATE and
    as the FK target of tbl_model_sub_types.model_id. Verified empty and
    unreferenced on 2026-11-02, then removed on the owner's instruction."""
    assert table not in inline_sql_tables()


@pytest.mark.parametrize("table", DEAD_PAIR)
def test_nothing_alters_seeds_or_queries_the_dead_tables(table):
    """Removing a CREATE while something still names the table would move the
    failure to startup, against a live database — exactly the class of defect
    test_every_altered_or_seeded_table_is_also_created exists to catch."""
    for stmt in _sql_literals(MAIN):
        assert table not in stmt.lower(), stmt[:160]


class _FakeConn:
    """Records the SQL it is handed and answers COUNT(*) with `rows`."""

    def __init__(self, rows=0, fail_on=()):
        self.rows = rows
        self.fail_on = fail_on
        self.executed = []

    async def execute(self, clause):
        sql = str(clause)
        self.executed.append(sql)
        for frag in self.fail_on:
            if frag in sql:
                raise RuntimeError("table missing")
        if "COUNT(*)" in sql:
            class _R:
                def __init__(self, n): self._n = n
                def scalar(self): return self._n
            return _R(self.rows)
        return None


@pytest.mark.asyncio
async def test_an_empty_pair_is_dropped_child_first():
    """The FK is tbl_model_sub_types.model_id -> tbl_all_models, so the parent
    cannot go first — MySQL rejects it."""
    import app.main as main_mod

    conn = _FakeConn(rows=0)
    await main_mod._drop_dead_model_tables(conn)
    drops = [s for s in conn.executed if s.startswith("DROP TABLE")]
    assert len(drops) == 2, conn.executed
    assert "tbl_model_sub_types" in drops[0]
    assert "tbl_all_models" in drops[1]


@pytest.mark.asyncio
async def test_a_NON_empty_table_is_never_dropped():
    """The guard that makes this safe to ship rather than merely safe here.

    Both were measured at 0 rows on 2026-11-02, but PRODUCTION RUNS ON ANOTHER
    MACHINE whose contents cannot be inspected from here. A bare
    `DROP TABLE IF EXISTS` in the startup path would run there too and take
    whatever it found. The owner's instruction was conditional — "if it is
    empty tables and does not use anywhere" — so the condition is enforced in
    code rather than inferred from one database's state.
    """
    import app.main as main_mod

    conn = _FakeConn(rows=3)
    await main_mod._drop_dead_model_tables(conn)
    assert not [s for s in conn.executed if s.startswith("DROP TABLE")], conn.executed


@pytest.mark.asyncio
async def test_a_missing_table_is_not_an_error():
    """A fresh deployment never had them; startup must not fail over that."""
    import app.main as main_mod

    conn = _FakeConn(rows=0, fail_on=("COUNT(*)",))
    await main_mod._drop_dead_model_tables(conn)   # must not raise
    assert not [s for s in conn.executed if s.startswith("DROP TABLE")]


@pytest.mark.asyncio
async def test_a_failing_drop_does_not_fail_the_deployment():
    import app.main as main_mod

    conn = _FakeConn(rows=0, fail_on=("DROP TABLE",))
    await main_mod._drop_dead_model_tables(conn)   # must not raise


def test_the_drop_order_is_the_foreign_key_order():
    """Asserted on the real tuple rather than on source text — an earlier
    version of this test grepped the function body, where the names do not
    appear at all because it iterates over this constant."""
    import app.main as main_mod

    order = list(main_mod.DEAD_MODEL_TABLES)
    assert order.index("tbl_model_sub_types") < order.index("tbl_all_models")


def test_the_lifespan_runs_the_guarded_drop():
    """A cleanup nothing calls leaves the tables in place on every existing
    deployment."""
    import inspect

    import app.main as main_mod

    assert "_drop_dead_model_tables" in inspect.getsource(main_mod.lifespan)
