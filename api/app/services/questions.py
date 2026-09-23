"""Questions to the candidate, chosen per listing by the manager (optional; the candidate may skip them).

Ready-made questions are translated here into the 4 site languages; a manager's own question is a yes/no
with its text typed per language (free text is never machine-translated). Answers are stored as
{key: value}; the text of an own question is kept with the answer, so editing the listing later does not
change what the candidate was asked.
"""

from typing import Any

T = dict[str, str]

YES_NO: list[tuple[str, T]] = [
    ("yes", {"es": "Sí", "en": "Yes", "uk": "Так", "ru": "Да"}),
    ("no", {"es": "No", "en": "No", "uk": "Ні", "ru": "Нет"}),
]

PRESETS: dict[str, tuple[T, list[tuple[str, T]]]] = {
    "licence_c": (
        {
            "es": "¿Tienes carnet C?",
            "en": "Do you have a C driving licence?",
            "uk": "Є права категорії C?",
            "ru": "Есть права категории C?",
        },
        YES_NO,
    ),
    "licence_ce": (
        {
            "es": "¿Tienes carnet C+E?",
            "en": "Do you have a CE driving licence?",
            "uk": "Є права категорії CE?",
            "ru": "Есть права категории CE?",
        },
        YES_NO,
    ),
    "code95": (
        {
            "es": "¿Tienes el CAP (código 95)?",
            "en": "Do you have the CPC (code 95)?",
            "uk": "Є код 95 (CAP)?",
            "ru": "Есть код 95 (CAP)?",
        },
        YES_NO,
    ),
    "tacho": (
        {
            "es": "¿Tienes tarjeta de tacógrafo?",
            "en": "Do you have a tachograph card?",
            "uk": "Є картка тахографа?",
            "ru": "Есть карта тахографа?",
        },
        YES_NO,
    ),
    "work_permit": (
        {
            "es": "¿Tienes NIE y permiso de trabajo en España?",
            "en": "Do you have an NIE and a work permit in Spain?",
            "uk": "Є NIE і дозвіл на роботу в Іспанії?",
            "ru": "Есть NIE и разрешение на работу в Испании?",
        },
        YES_NO,
    ),
    "start": (
        {
            "es": "¿Cuándo puedes empezar?",
            "en": "When can you start?",
            "uk": "Коли можете почати?",
            "ru": "Когда можете начать?",
        },
        [
            ("now", {"es": "Ya mismo", "en": "Right away", "uk": "Одразу", "ru": "Сразу"}),
            ("week", {"es": "En una semana", "en": "In a week", "uk": "За тиждень", "ru": "Через неделю"}),
            ("later", {"es": "Más adelante", "en": "Later", "uk": "Пізніше", "ru": "Позже"}),
        ],
    ),
    "experience": (
        {
            "es": "¿Cuánta experiencia tienes en este trabajo?",
            "en": "How much experience do you have in this job?",
            "uk": "Скільки маєте досвіду на такій роботі?",
            "ru": "Сколько у вас опыта на такой работе?",
        },
        [
            ("none", {"es": "Ninguna", "en": "None", "uk": "Немає", "ru": "Нет"}),
            ("lt1", {"es": "Menos de 1 año", "en": "Under 1 year", "uk": "До 1 року", "ru": "До 1 года"}),
            ("1to3", {"es": "1–3 años", "en": "1–3 years", "uk": "1–3 роки", "ru": "1–3 года"}),
            (
                "gt3",
                {"es": "Más de 3 años", "en": "Over 3 years", "uk": "Понад 3 роки", "ru": "Больше 3 лет"},
            ),
        ],
    ),
    "spanish": (
        {
            "es": "¿Qué nivel de español tienes?",
            "en": "How well do you speak Spanish?",
            "uk": "Як ви говорите іспанською?",
            "ru": "Как вы говорите по-испански?",
        },
        [
            ("none", {"es": "No lo hablo", "en": "Not at all", "uk": "Не говорю", "ru": "Не говорю"}),
            ("basic", {"es": "Básico", "en": "Basic", "uk": "Базово", "ru": "Базово"}),
            ("fluent", {"es": "Con soltura", "en": "Fluently", "uk": "Вільно", "ru": "Свободно"}),
        ],
    ),
    "own_car": (
        {
            "es": "¿Tienes coche propio?",
            "en": "Do you have your own car?",
            "uk": "Є власне авто?",
            "ru": "Есть собственная машина?",
        },
        YES_NO,
    ),
    "nights": (
        {
            "es": "¿Puedes trabajar en turno de noche?",
            "en": "Can you work night shifts?",
            "uk": "Готові працювати в нічні зміни?",
            "ru": "Готовы работать в ночные смены?",
        },
        YES_NO,
    ),
    "relocate": (
        {
            "es": "¿Puedes mudarte a otra ciudad?",
            "en": "Can you move to another city?",
            "uk": "Готові переїхати в інше місто?",
            "ru": "Готовы переехать в другой город?",
        },
        YES_NO,
    ),
}

MAX_QUESTIONS = 6
CUSTOM_KEYS = ("custom1", "custom2")
LANGS = ("es", "en", "uk", "ru")


def _pick(texts: T, lang: str) -> str:
    """The visitor's language, else Spanish, else the first one filled (the site-wide fallback)."""
    return texts.get(lang) or texts.get("es") or next((v for v in texts.values() if v), "")


def clean(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """What the admin form sent -> what is stored: known presets and filled own questions, no repeats."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for q in questions:
        key = q.get("key")
        if not isinstance(key, str) or key in seen:
            continue
        if key in PRESETS:
            out.append({"key": key})
        elif key in CUSTOM_KEYS:
            text = {
                lang: str(v).strip()[:200] for lang, v in (q.get("text") or {}).items() if lang in LANGS and v
            }
            if not any(text.values()):
                continue
            out.append({"key": key, "text": text})
        else:
            continue
        seen.add(key)
    return out[:MAX_QUESTIONS]


def options_of(q: dict[str, Any]) -> list[tuple[str, T]]:
    return PRESETS[q["key"]][1] if q["key"] in PRESETS else YES_NO


def text_of(q: dict[str, Any]) -> T:
    return PRESETS[q["key"]][0] if q["key"] in PRESETS else q.get("text") or {}


def public(questions: list[dict[str, Any]], lang: str) -> list[dict[str, Any]]:
    """For the job page: the question and its answer buttons in the visitor's language."""
    return [
        {
            "key": q["key"],
            "text": _pick(text_of(q), lang),
            "options": [{"value": value, "label": _pick(label, lang)} for value, label in options_of(q)],
        }
        for q in questions
        if q.get("key") in PRESETS or q.get("key") in CUSTOM_KEYS
    ]


def answers_for(questions: list[dict[str, Any]], answers: dict[str, str]) -> list[dict[str, Any]]:
    """The candidate's answers, checked against the listing's questions; unknown keys and values are dropped.
    Stored with the question's texts so the manager sees exactly what was asked."""
    out = []
    for q in questions:
        value = answers.get(q["key"])
        if value and value in {v for v, _ in options_of(q)}:
            out.append({"key": q["key"], "value": value, "text": text_of(q)})
    return out


def describe(answer: dict[str, Any], lang: str) -> dict[str, str]:
    """An answer as the admin shows it, in the admin language."""
    labels = dict(options_of({"key": answer["key"]}) if answer["key"] in PRESETS else YES_NO)
    return {
        "question": _pick(answer.get("text") or {}, lang),
        "answer": _pick(labels.get(answer["value"], {}), lang) or answer["value"],
    }
