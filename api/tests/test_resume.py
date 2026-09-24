"""What the CV form accepts and what it quietly tidies up."""

import pytest
from pydantic import ValidationError

from app.schemas.resume import ResumeIn


def test_the_shortest_useful_cv_is_a_headline() -> None:
    resume = ResumeIn(title="  Водій категорії CE  ")
    assert resume.title == "Водій категорії CE"
    assert resume.about == ""
    assert resume.licences == [] and resume.languages == {}
    assert resume.is_public is True


def test_repeated_licences_and_schedules_are_folded() -> None:
    resume = ResumeIn(title="Будівельник", licences=["ce", "b", "ce"], schedule=["full", "full"])
    assert resume.licences == ["b", "ce"]
    assert resume.schedule == ["full"]


def test_an_unknown_licence_or_level_is_refused() -> None:
    with pytest.raises(ValidationError):
        ResumeIn(title="Водій", licences=["tractor"])
    with pytest.raises(ValidationError):
        ResumeIn(title="Водій", languages={"es": "fluent"})
    with pytest.raises(ValidationError):
        ResumeIn(title="Водій", languages={"pl": "b1"})


def test_a_headline_of_two_letters_is_not_a_job() -> None:
    with pytest.raises(ValidationError):
        ResumeIn(title="CE")


def test_experience_stays_within_a_working_life() -> None:
    assert ResumeIn(title="Кухар", experience_years=0).experience_years == 0
    with pytest.raises(ValidationError):
        ResumeIn(title="Кухар", experience_years=61)
