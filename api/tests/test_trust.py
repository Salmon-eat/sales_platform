"""The rules around complaints and reviews that hold without a database."""

import pytest
from pydantic import ValidationError

from app.api.routes.my import ReplyIn, ReviewIn
from app.api.routes.reports import ReportIn
from app.models.report import REPORT_REASONS


def test_a_complaint_needs_a_reason_we_know() -> None:
    report = ReportIn(listing_id=7, reason="fraud", note="  просить передоплату  ")
    assert report.note == "просить передоплату"
    with pytest.raises(ValidationError):
        ReportIn(listing_id=7, reason="i just do not like it")


def test_every_reason_offered_in_the_admin_is_accepted() -> None:
    for reason in REPORT_REASONS:
        assert ReportIn(listing_id=1, reason=reason).reason == reason


def test_an_empty_note_is_no_note() -> None:
    assert ReportIn(listing_id=1, reason="spam", note="   ").note is None
    assert ReportIn(listing_id=1, reason="spam").note is None


def test_a_rating_is_one_to_five_stars() -> None:
    assert ReviewIn(seller_id=2, rating=5).rating == 5
    for bad in (0, 6, -1):
        with pytest.raises(ValidationError):
            ReviewIn(seller_id=2, rating=bad)


def test_a_review_may_be_stars_without_words_but_a_reply_may_not_be_empty() -> None:
    assert ReviewIn(seller_id=2, rating=4).text == ""
    with pytest.raises(ValidationError):
        ReplyIn(text="")
