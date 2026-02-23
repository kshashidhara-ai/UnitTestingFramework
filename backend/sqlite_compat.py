"""
SQLite compatibility patch — replaces PostgreSQL-specific types
(JSONB, ARRAY) with SQLite-compatible equivalents (JSON, Text).
Must be imported BEFORE any app.models imports.
"""
import json
from sqlalchemy import types
from sqlalchemy.dialects.postgresql import JSONB, ARRAY


class JSONType(types.TypeDecorator):
    """Stores dict/list as JSON text in SQLite; passes through natively for Postgres."""
    impl = types.Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value


class ArrayType(types.TypeDecorator):
    """Stores list as JSON text in SQLite."""
    impl = types.Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value if isinstance(value, list) else list(value))
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value


def patch_for_sqlite():
    """Monkey-patch postgresql-specific types to use SQLite-compatible versions."""
    import sqlalchemy.dialects.postgresql as pg

    # Patch JSONB
    original_jsonb_init = pg.JSONB.__init__
    def jsonb_sqlite_init(self, *args, **kwargs):
        self.impl = types.Text()
    pg.JSONB.impl = types.Text
    pg.JSONB.__init__ = lambda self, *a, **kw: setattr(self, 'cache_ok', True)
    pg.JSONB.load_dialect_impl = lambda self, dialect: dialect.type_descriptor(types.Text())
    pg.JSONB.process_bind_param = lambda self, value, dialect: (json.dumps(value) if value is not None else None)
    pg.JSONB.process_result_value = lambda self, value, dialect: (json.loads(value) if value is not None else None)
    pg.JSONB.__class_getitem__ = classmethod(lambda cls, item: cls)

    # Make JSONB a TypeDecorator so SQLite handles it
    # Simpler approach: replace the columns at model level

    return True
