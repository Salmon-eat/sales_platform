import pytest
from fastapi import HTTPException

from app.services import cv, questions

PDF = b"%PDF-1.7\n1 0 obj\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 20
DOCX = b"PK\x03\x04" + b"\0" * 26 + b"[Content_Types].xml word/document.xml"


def test_manager_questions_are_cleaned():
    stored = questions.clean(
        [
            {"key": "licence_ce"},
            {"key": "licence_ce"},  # repeated
            {"key": "hack"},  # unknown
            {"key": "custom1", "text": {"uk": "Можете почати в понеділок?", "xx": "?"}},
            {"key": "custom2", "text": {"uk": "  "}},  # empty own question
        ]
    )
    assert stored == [{"key": "licence_ce"}, {"key": "custom1", "text": {"uk": "Можете почати в понеділок?"}}]


def test_questions_show_in_the_visitors_language_with_fallback():
    shown = questions.public([{"key": "start"}, {"key": "custom1", "text": {"uk": "Є інструменти?"}}], "es")
    assert shown[0]["text"] == "¿Cuándo puedes empezar?"
    assert [o["label"] for o in shown[0]["options"]] == ["Ya mismo", "En una semana", "Más adelante"]
    assert shown[1]["text"] == "Є інструменти?"  # own question only in Ukrainian: shown as written
    assert [o["value"] for o in shown[1]["options"]] == ["yes", "no"]


def test_answers_are_checked_against_the_listing():
    asked = [{"key": "licence_ce"}, {"key": "experience"}]
    answers = questions.answers_for(asked, {"licence_ce": "yes", "experience": "forever", "own_car": "yes"})
    assert [(a["key"], a["value"]) for a in answers] == [("licence_ce", "yes")]
    assert questions.describe(answers[0], "uk") == {"question": "Є права категорії CE?", "answer": "Так"}


def test_cv_type_comes_from_the_content_not_the_name():
    assert cv.detect(PDF)[1] == "pdf"
    assert cv.detect(PNG)[1] == "png"
    assert cv.detect(DOCX)[1] == "docx"
    for bad in (b"MZ\x90\x00 an exe", b"<html><script>", b"PK\x03\x04 just a zip"):
        with pytest.raises(HTTPException) as error:
            cv.detect(bad)
        assert error.value.status_code == 415


def test_cv_names_are_made_safe():
    assert cv.safe_name('../../etc/passwd"; x.exe', "pdf") == "etcpasswd x.pdf"
    assert cv.safe_name("Резюме Олена.docx", "docx") == "Резюме Олена.docx"
    assert cv.safe_name("", "png") == "cv.png"
