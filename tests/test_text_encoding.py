import pytest

from core.text_encoding import make_encodable


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Wizz Air Hungary Légiközlekedési Zrt.", "Wizz Air Hungary Legikozlekedesi Zrt."),
        ("Søren Ærø", "Soren AEro"),
        ("Straße", "Strasse"),
        ("Müller", "Muller"),
        ("Łódź", "Lodz"),
        ("ë č ć ă š é ș ç", "e c c a s e s c"),
    ],
)
def test_transliterates_letters_cp1251_cannot_hold(text, expected):
    assert make_encodable(text, "cp1251") == (expected, False)


@pytest.mark.parametrize(
    "text",
    [
        "ЕМИЛИЯ ТАШЕВА ГЮРОВА",
        "Рикрутив ЕООД, бул. „Александър Малинов“ № 23",
        "Йордан Шишков – Ёж",  # й and ё decompose under NFKD but are valid cp1251
    ],
)
def test_keeps_text_cp1251_supports(text):
    assert make_encodable(text, "cp1251") == (text, False)


def test_falls_back_to_question_mark():
    assert make_encodable("Tour 😊 ok", "cp1251") == ("Tour ? ok", True)
