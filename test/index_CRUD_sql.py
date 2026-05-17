from backend.db import supabase


class FakeExecuteResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, table_name):
        self.table_name = table_name
        self.operations = []

    def insert(self, data):
        self.operations.append(("insert", data))
        self.data = [{**data, "id": "created-row"}]
        return self

    def upsert(self, data, on_conflict="id"):
        self.operations.append(("upsert", data, on_conflict))
        self.data = [data]
        return self

    def select(self, columns):
        self.operations.append(("select", columns))
        self.data = [{"id": "row-1"}]
        return self

    def eq(self, column, value):
        self.operations.append(("eq", column, value))
        return self

    def execute(self):
        return FakeExecuteResponse(self.data)


class FakeSupabaseClient:
    def __init__(self):
        self.queries = []

    def table(self, table_name):
        query = FakeQuery(table_name)
        self.queries.append(query)
        return query


def test_insert_row_uses_supabase_insert(monkeypatch):
    client = FakeSupabaseClient()
    monkeypatch.setattr(supabase, "get_supabase_client", lambda: client)

    row = supabase.insert_row("courses", {"title": "POO"})

    assert row == {"title": "POO", "id": "created-row"}
    assert client.queries[0].table_name == "courses"
    assert client.queries[0].operations == [("insert", {"title": "POO"})]


def test_upsert_row_uses_conflict_key(monkeypatch):
    client = FakeSupabaseClient()
    monkeypatch.setattr(supabase, "get_supabase_client", lambda: client)

    row = supabase.upsert_row("users", {"id": "user-1", "email": "a@n7.local"}, on_conflict="email")

    assert row["id"] == "user-1"
    assert client.queries[0].operations == [
        ("upsert", {"id": "user-1", "email": "a@n7.local"}, "email")
    ]


def test_select_rows_applies_filters(monkeypatch):
    client = FakeSupabaseClient()
    monkeypatch.setattr(supabase, "get_supabase_client", lambda: client)

    rows = supabase.select_rows("courses", "id,title", {"module_id": "module-1"})

    assert rows == [{"id": "row-1"}]
    assert client.queries[0].operations == [
        ("select", "id,title"),
        ("eq", "module_id", "module-1"),
    ]


def test_fetch_all_uses_connection_cursor(monkeypatch):
    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def execute(self, query, params=None):
            self.query = query
            self.params = params

        def fetchall(self):
            return [{"id": "row-1"}]

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr(supabase, "get_connection", lambda: FakeConnection())

    assert supabase.fetch_all("SELECT 1", {"x": 1}) == [{"id": "row-1"}]
