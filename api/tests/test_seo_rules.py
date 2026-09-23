from datetime import UTC, datetime, timedelta

from app.seo.paths import feature_by_slug, list_path, listing_path, offer_word_lang, parse_listing_tail
from app.seo.rules import IndexState, closed_state, next_index_state, threshold_of, tier_of

NOW = datetime(2026, 9, 17, 12, tzinfo=UTC)


def test_thresholds_from_the_spec() -> None:
    assert threshold_of(None, False, False) == 0  # L1 always
    assert threshold_of(None, True, False) == 3  # L1 + location
    assert threshold_of("sector", False, False) == 1
    assert threshold_of("sector", True, False) == 3
    assert threshold_of("profession", False, False) == 1
    assert threshold_of("profession", True, False) == 3
    assert threshold_of(None, False, True) == 3  # with housing
    assert tier_of("profession", True, True) == "L3+feature+loc"


def test_hysteresis_keeps_a_page_indexed_for_14_days() -> None:
    state = next_index_state(IndexState(False, None), count=5, threshold=3, now=NOW)
    assert state == IndexState(True, None)

    dropped = next_index_state(state, count=1, threshold=3, now=NOW)
    assert dropped == IndexState(True, NOW)  # still indexed, the clock starts

    later = next_index_state(dropped, count=2, threshold=3, now=NOW + timedelta(days=13))
    assert later.indexable

    gone = next_index_state(later, count=2, threshold=3, now=NOW + timedelta(days=14))
    assert not gone.indexable

    back = next_index_state(gone, count=3, threshold=3, now=NOW + timedelta(days=20))
    assert back == IndexState(True, None)


def test_never_indexed_page_stays_out() -> None:
    assert not next_index_state(IndexState(False, None), count=2, threshold=3, now=NOW).indexable


def test_closed_card_timeline() -> None:
    assert closed_state(NOW - timedelta(days=5), NOW) == "closed"
    assert closed_state(NOW - timedelta(days=31), NOW) == "closed_noindex"
    assert closed_state(NOW - timedelta(days=91), NOW) == "gone"


def test_paths() -> None:
    assert list_path("robota", "transport", "vodii-ce", None, "madrid") == "robota/transport/vodii-ce/madrid"
    assert (
        listing_path("empleo", "es", "conductor-ce-madrid", 12345)
        == "empleo/oferta/conductor-ce-madrid-12345"
    )
    assert parse_listing_tail("conductor-ce-madrid-12345") == ("conductor-ce-madrid", 12345)
    assert parse_listing_tail("no-id-here") is None
    assert feature_by_slug("z-zhytlom") == ("housing", "uk")
    assert offer_word_lang("vakansiia") == "uk"
    # outside jobs a card is an "ad", not a vacancy
    assert listing_path("rechi", "uk", "dyvan-madrid", 42, "articulos") == "rechi/oholoshennia/dyvan-madrid-42"
    assert listing_path("motor", "es", "ford-transit", 7, "motor") == "motor/anuncio/ford-transit-7"
    assert offer_word_lang("anuncio") == "es"
    assert offer_word_lang("oholoshennia") == "uk"
    assert offer_word_lang("something-else") is None
