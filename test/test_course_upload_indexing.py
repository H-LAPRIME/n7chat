from backend.flows.document_extract_flow import extract_text_from_bytes
from backend.flows import index_flow
from backend.flows.index_flow import chunk_text
from backend.routers import courses


def test_extract_text_from_plain_text_upload():
    text = extract_text_from_bytes(
        filename="poo.txt",
        content=b"Classe Objet Heritage",
        content_type="text/plain",
    )

    assert text == "Classe Objet Heritage"


def test_uploaded_course_text_can_be_chunked_for_embedding():
    extracted = " ".join(f"word{i}" for i in range(20))
    chunks = chunk_text(extracted, size=8, overlap=2)

    assert chunks[0] == "word0 word1 word2 word3 word4 word5 word6 word7"
    assert chunks[1].startswith("word6 word7")


async def _run_index_admin_document(monkeypatch):
    captured = {}

    async def fake_index_document(**kwargs):
        captured.update(kwargs)
        return 2

    monkeypatch.setattr(index_flow, "index_document", fake_index_document)

    count = await index_flow.index_admin_document_upload(
        storage_path="admin/user-1/reglement.pdf",
        public_url="https://storage/documents/reglement.pdf",
        title="Reglement",
        content="Le reglement pedagogique",
        file_type="pdf",
        uploaded_by="user-1",
        description="Document administratif",
    )
    return count, captured


def test_admin_document_upload_indexes_as_admin_document(monkeypatch):
    import asyncio

    count, captured = asyncio.run(_run_index_admin_document(monkeypatch))

    assert count == 2
    assert captured["source_type"] == "admin_document"
    assert captured["source_table"] == "storage.documents"
    assert captured["source_url"] == "https://storage/documents/reglement.pdf"
    assert captured["metadata"]["storage_path"] == "admin/user-1/reglement.pdf"
    assert captured["metadata"]["uploaded_by"] == "user-1"


def test_auto_create_upload_module(monkeypatch):
    calls = []

    def fake_fetch_one(query, params):
        calls.append((query, params))
        if "SELECT id FROM modules WHERE code" in query:
            return None
        if "INSERT INTO modules" in query:
            return {"id": "module-created"}
        return None

    monkeypatch.setattr(courses, "fetch_one", fake_fetch_one)

    module_id = courses._create_upload_module(
        {"filiere_id": "59a46832-5d35-5fb2-bea6-3f48a11fc279", "semester": "3"},
        {"role": "teacher", "teacher_id": "teacher-1"},
        "Theorie des graphes",
    )

    assert module_id == "module-created"
    insert_params = calls[-1][1]
    assert insert_params["teacher_id"] == "teacher-1"
    assert insert_params["name"] == "Theorie des graphes"
    assert insert_params["code"] == "THEORIE-DES-GRAPHES"
