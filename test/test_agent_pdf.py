from pathlib import Path

from backend.agents.pdf_agent import _infer_report_type, build_pdf_report_sync
from backend.tasks.pdf_llm_task import build_dynamic_report_spec
from backend.tools.pdf_tool import _latex_to_readable_text, build_bulletin_pdf, build_notes_pdf, build_timetable_pdf


def test_infer_report_type():
    assert _infer_report_type("genere mes notes pdf") == "report"
    assert _infer_report_type("resume la derniere reponse en pdf") == "summary"
    assert _infer_report_type("anything", "bulletin") == "bulletin"


def test_build_notes_pdf_creates_file():
    path = build_notes_pdf(
        {"first_name": "Sara", "last_name": "Test", "filiere_name": "GI", "level_name": "L2"},
        [
            {
                "module_name": "Bases de donnees",
                "exam_type": "cc",
                "score": 16,
                "coefficient": 0.4,
                "published_at": "2026-05-17",
            }
        ],
    )

    assert Path(path).exists()
    assert Path(path).suffix == ".pdf"


def test_build_bulletin_pdf_creates_file():
    path = build_bulletin_pdf(
        {"first_name": "Omar", "last_name": "Test", "filiere_name": "GI", "level_name": "L2"},
        [{"module_name": "Algo", "exam_type": "exam", "score": 13, "semester": 3}],
        [{"module_name": "Algo", "date": "2026-05-05", "justified": False}],
    )

    assert Path(path).exists()
    assert Path(path).suffix == ".pdf"


def test_build_timetable_pdf_creates_file():
    path = build_timetable_pdf(
        {"first_name": "Omar", "last_name": "Test", "filiere_name": "GI", "level_name": "L2"},
        [{"module_name": "Algo", "module_code": "GI-S3-ALG", "semester": 3, "teacher_first_name": "Youssef"}],
        [{"title": "Conference IA", "event_type": "conference", "start_date": "2026-05-28 12:00", "location": "Salle"}],
    )

    assert Path(path).exists()
    assert Path(path).suffix == ".pdf"


def test_pdf_math_latex_is_converted_to_readable_symbols():
    text = (
        r"Vecteurs dans \( \mathbb{R}^n \) : "
        r"\( u \cdot v = \sum u_i v_i \), "
        r"\( \|u\| = \sqrt{\sum u_i^2} \), "
        r"\( A \times B \neq B \times A \)."
    )

    rendered = _latex_to_readable_text(text)

    assert r"\(" not in rendered
    assert r"\mathbb" not in rendered
    assert r"\sum" not in rendered
    assert "ℝⁿ" in rendered
    assert "∑" in rendered
    assert "√(" in rendered
    assert "×" in rendered
    assert "≠" in rendered


def test_dynamic_report_spec_is_section_based():
    spec = build_dynamic_report_spec(
        message="genere un rapport avec notes et absences",
        selected_type="bulletin",
        student={"first_name": "Sara", "last_name": "Test", "filiere_name": "GI"},
        notes=[{"module_name": "Algo", "exam_type": "cc", "score": 15}],
        absences=[{"module_name": "Algo", "date": "2026-05-05", "justified": True}],
    )

    assert spec["type"] == "bulletin"
    assert [section["title"] for section in spec["sections"]] == ["Notes", "Absences"]
    assert spec["sections"][0]["rows"][0]["module_name"] == "Algo"


def test_dynamic_report_spec_supports_document_reports():
    spec = build_dynamic_report_spec(
        message="genere un rapport PDF sur ce document administratif",
        selected_type="document",
        student={"first_name": "Sara", "last_name": "Test"},
        notes=[],
        absences=[],
        data_context={
            "rag": {"context": "Reglement: les inscriptions se font en septembre."},
            "sources": [{"title": "Reglement", "source_type": "admin_document", "source_name": "reglement.pdf"}],
        },
    )

    assert spec["type"] == "document"
    assert [section["title"] for section in spec["sections"]] == ["Contenu disponible", "Sources"]


def test_build_pdf_report_sync_uses_tools(monkeypatch):
    monkeypatch.setattr(
        "backend.agents.pdf_agent.get_student_profile",
        lambda **_: {"ok": True, "data": {"first_name": "Sara", "last_name": "Test"}},
    )
    result = build_pdf_report_sync(
        "bulletin pdf",
        {"id": "user-1", "student_id": "student-1"},
        data_context={"last_assistant_response": "Voici un bilan academique structure."},
    )

    assert result["ok"] is True
    assert result["artifact"]["type"] == "report"
    assert result["artifact"]["report_spec"]["sections"][0]["title"] == "Synthese"
    assert Path(result["artifact"]["file_path"]).exists()


def test_build_pdf_report_sync_generates_timetable(monkeypatch):
    monkeypatch.setattr(
        "backend.agents.pdf_agent.get_student_profile",
        lambda **_: {"ok": True, "data": {"first_name": "Omar", "last_name": "Test", "filiere_id": "filiere-1"}},
    )
    result = build_pdf_report_sync(
        "horaire sous format pdf",
        {"id": "user-1", "student_id": "student-1", "filiere_id": "filiere-1"},
        data_context={
            "sql": {
                "modules": {"ok": True, "data": [{"module_name": "Algo", "module_code": "GI-S3-ALG"}]},
                "events": {"ok": True, "data": [{"title": "Conference IA"}]},
            }
        },
    )

    assert result["ok"] is True
    assert result["artifact"]["type"] == "report"
    section_titles = [section["title"] for section in result["data"]["report"]["sections"]]
    assert "Modules" in section_titles
    assert Path(result["artifact"]["file_path"]).exists()


def test_build_pdf_report_sync_uses_rag_context_for_document_report():
    result = build_pdf_report_sync(
        "genere un rapport pdf sur ce document administratif",
        {"id": "user-1"},
        data_context={
            "rag": {"context": "Reglement des examens et calendrier administratif."},
            "sources": [{"title": "Reglement examens", "source_type": "admin_document"}],
        },
    )

    assert result["ok"] is True
    assert result["artifact"]["type"] == "report"
    assert result["data"]["report"]["sections"][0]["title"] == "Contenu disponible"
    assert Path(result["artifact"]["file_path"]).exists()


def test_build_pdf_report_sync_cleans_and_structures_last_answer():
    answer = """Je ne peux pas generer un emploi du temps au format PDF, car les donnees manquantes.

---

Voici l'emploi du temps pour GEER1.

### Resume de l'emploi du temps

| Jour | 08h30 - 10h30 | 10h30 - 12h30 |
| --- | --- | --- |
| Lundi | Machines Electriques | Communication |
| Mardi | Identification et Regulation | Traitement du Signal |

### Notes

- Salles principales : 3 et 8.
- Version provisoire.
"""
    result = build_pdf_report_sync(
        "genere sous format pdf",
        {"id": "user-1", "first_name": "Amal", "last_name": "Benali"},
        data_context={"last_assistant_response": answer},
    )

    sections = result["data"]["report"]["sections"]
    assert result["ok"] is True
    assert sections[0]["type"] == "list"
    assert "Je ne peux pas" not in str(sections)
    assert any(section["type"] == "table" and section["title"] == "Resume de l'emploi du temps" for section in sections)
    assert any(section["title"] == "Notes" for section in sections)


def test_build_pdf_report_sync_exports_last_timetable_response():
    result = build_pdf_report_sync(
        "genere sous format pdf",
        {"id": "user-1", "first_name": "Amal", "last_name": "Benali"},
        data_context={
            "rag": {"context": "EMPLOI DU TEMPS 2025/2026 FI - GEER\nLundi: Machines Electriques."},
            "sources": [{"title": "Emploi de temp", "source_type": "timetable"}],
            "last_assistant_response": "Voici l'emploi du temps GEER organise par jour.",
        },
    )

    assert result["ok"] is True
    assert result["artifact"]["type"] == "report"
    section_titles = [section["title"] for section in result["data"]["report"]["sections"]]
    assert "Synthese" in section_titles
    assert "Contenu disponible" not in section_titles
    assert "Notes" not in section_titles
    assert Path(result["artifact"]["file_path"]).exists()


def test_build_pdf_report_sync_de_ca_uses_only_previous_answer():
    previous = """Voici un résumé du cours de Français (Grammaire & Expression écrite) destiné aux étudiants en Génie Informatique.

---

1. Les Types de phrases
- Déclarative : énoncer un fait.
- Interrogative : poser une question.

2. La Ponctuation
- Le point termine une phrase.
- La virgule sépare des éléments.
"""

    result = build_pdf_report_sync(
        "genere pdf de ca",
        {"id": "user-1", "first_name": "Salim", "last_name": "Test"},
        data_context={
            "rag": {"context": "EMPLOI DU TEMPS 2025/2026 FI - GEER\nLundi: Machines Electriques."},
            "sources": [{"title": "Emploi de temp", "source_type": "timetable"}],
        },
        history=[{"role": "assistant", "content": previous}],
    )

    report = result["data"]["report"]
    assert result["ok"] is True
    assert report["title"] == "Rapport PDF"
    assert "Emploi de temp" not in str(report)
    assert "Types de phrases" in str(report)
    assert "Ponctuation" in str(report)
