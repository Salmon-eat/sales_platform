"""The automatic look at an ad: it flags, it does not judge."""

from app.services.screening import check_text


def test_a_normal_ad_is_clean() -> None:
    assert check_text(
        "Диван розкладний, майже новий",
        "Диван у гарному стані, розкладається, тканина сіра. Самовивіз у Валенсії.",
    ) == []


def test_a_phone_in_the_text_is_noticed() -> None:
    assert "contact_in_text" in check_text("Продам диван", "Телефонуйте +34 600 111 222")
    assert "contact_in_text" in check_text("Продам диван", "Пишіть на test@mail.com")
    assert "contact_in_text" in check_text("Продам диван", "Мій телеграм @sellersofa")


def test_a_link_in_the_title_is_noticed_separately() -> None:
    flags = check_text("Диван дешево www.example.com", "Опис без контактів взагалі")
    assert flags == ["contact_in_text", "link_in_title"]


def test_the_stop_words_are_matched_by_stem_in_every_language() -> None:
    assert "stop_word:money" in check_text("Швидкий заробіток", "Потрібна передоплата, потім віддамо")
    assert "stop_word:money" in check_text("Trabajo fácil", "Se pide dinero rápido por adelantado")
    assert "stop_word:papers" in check_text("Carnet sin examen", "Документи без іспиту, швидко")


def test_punctuation_does_not_hide_a_stop_word() -> None:
    assert "stop_word:papers" in check_text("Купить-права!", "Терміново, без іспитів")


def test_a_price_is_not_a_phone_number() -> None:
    assert check_text("Велосипед", "Продам за 250 євро, стан гарний, зимою не користувався") == []
