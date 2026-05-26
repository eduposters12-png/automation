from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.elements import TextClause


def sqlite_sync_url(database_url: str) -> str:
    if database_url.startswith("sqlite+aiosqlite"):
        return database_url.replace("sqlite+aiosqlite", "sqlite", 1)
    return database_url


def patch_sqlite_alembic_operations() -> None:
    from alembic.operations import Operations

    if getattr(Operations.execute, "_listifyai_sqlite_patched", False):
        return

    original_execute = Operations.execute

    def execute(self, sqltext, *args, **kwargs):
        if isinstance(sqltext, str) and sqltext.strip().upper().startswith("ALTER TYPE "):
            return None
        return original_execute(self, sqltext, *args, **kwargs)

    execute._listifyai_sqlite_patched = True
    Operations.execute = execute


@compiles(postgresql.UUID, "sqlite")
def compile_postgresql_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(32)"


@compiles(postgresql.JSONB, "sqlite")
def compile_postgresql_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(TextClause, "sqlite")
def compile_text_clause_sqlite(element, compiler, **kw):
    if element.text.strip().lower() == "now()":
        return "CURRENT_TIMESTAMP"
    return compiler.visit_textclause(element, **kw)
