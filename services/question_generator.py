import re

import httpx
from openai import OpenAI
from langchain.docstore.document import Document

from config import settings


# ── Subtopics for GPT-only topics (no document) ───────────────────────────────

TOPIC_SUBTOPICS: dict[str, list[str]] = {
    "C++": [
        "Базовый синтаксис и типы данных",
        "Указатели и ссылки",
        "Объектно-ориентированное программирование",
        "Управление памятью (new/delete, RAII)",
        "STL: векторы, списки, карты",
        "Шаблоны (templates)",
        "Многопоточность (std::thread, mutex)",
        "Лямбда-функции и функторы",
        "Умные указатели (unique_ptr, shared_ptr)",
        "Исключения и обработка ошибок",
        "Перегрузка операторов",
        "Пространства имён (namespace)",
        "Компиляция и линковка",
        "Виртуальные функции и полиморфизм",
        "Move-семантика и rvalue-ссылки",
    ],
    "Go": [
        "Базовый синтаксис: переменные, типы, функции",
        "Структуры и методы",
        "Интерфейсы",
        "Горутины (goroutines)",
        "Каналы (channels) и select",
        "Обработка ошибок (error interface)",
        "Пакеты и модули (go mod)",
        "Срезы (slices) и карты (maps)",
        "Defer, panic, recover",
        "Контекст (context.Context)",
        "Работа с HTTP (net/http)",
        "Тестирование (testing package)",
        "Указатели в Go",
        "Мьютексы и sync.WaitGroup",
        "Рефлексия (reflect)",
    ],
    "SQL": [
        "SELECT: базовые запросы и фильтрация (WHERE)",
        "JOIN: INNER, LEFT, RIGHT, FULL",
        "GROUP BY и агрегатные функции",
        "Подзапросы и CTE (WITH)",
        "Оконные функции (OVER, PARTITION BY)",
        "Индексы и оптимизация запросов",
        "Транзакции и уровни изоляции",
        "DDL: CREATE, ALTER, DROP",
        "Нормализация баз данных",
        "HAVING и фильтрация агрегатов",
        "UNION, INTERSECT, EXCEPT",
        "Хранимые процедуры и функции",
        "Триггеры",
        "NULL и работа с пустыми значениями",
        "EXPLAIN и план запроса",
    ],
    "Аналитика данных": [
        "Описательная статистика: среднее, медиана, дисперсия",
        "Вероятность и распределения",
        "A/B тестирование и статистические гипотезы",
        "Работа с pandas: DataFrame, Series",
        "Очистка и предобработка данных",
        "Визуализация данных (matplotlib, seaborn)",
        "Корреляция и регрессионный анализ",
        "Метрики качества моделей ML",
        "Работа с временными рядами",
        "SQL для аналитики",
        "Кластеризация и сегментация",
        "Feature engineering",
        "Работа с пропущенными данными",
        "Основы Excel/Google Sheets для аналитики",
        "Построение дашбордов",
    ],
}


# ── HTTP client ────────────────────────────────────────────────────────────────

class _CustomHTTPClient(httpx.Client):
    def __init__(self, *args, **kwargs):
        kwargs.pop("proxies", None)
        super().__init__(*args, **kwargs)


def _get_client() -> OpenAI:
    return OpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        http_client=_CustomHTTPClient(),
    )


# ── Document-based generators ─────────────────────────────────────────────────

def generate_open_question(fragment: Document) -> str:
    """Generate a single open-ended question from a document fragment."""
    headers = fragment.metadata
    topic_title = headers.get("Header 1", "Unknown Topic")
    question_title = headers.get("Header 2", "Unknown Question")

    system = """
    Ты — нейро-экзаменатор, который всегда чётко выполняет инструкции.
    Твоя задача — сгенерировать открытый вопрос на основе предоставленного текста.
    Каждый вопрос должен быть коротким, конкретным и строго соответствовать сути текста.

    ВАЖНО:
    1. Если в тексте есть код — ОБЯЗАТЕЛЬНО включи его в ответ.
    2. Не задавай вопросы по коду, если его нет в ответе.
    3. Если задаёшь вопрос по коду — обязательно покажи релевантный код.
    """

    code_match = re.search(
        r"```(?:python|sql|cpp|go)?\s*(.*?)\s*```", fragment.page_content, re.DOTALL
    )
    code_block = ""
    if code_match:
        code = code_match.group(1).strip()
        if "SELECT" in code or "FROM" in code:
            lang = "sql"
        elif "#include" in code or "::" in code:
            lang = "cpp"
        elif "func " in code or "goroutine" in code:
            lang = "go"
        else:
            lang = "python"
        code_block = f"\n\nРассмотрите следующий код:\n```{lang}\n{code}\n```"

    user_prompt = (
        f"Тема: {topic_title}\n"
        f"Подтема: {question_title}\n"
        f"Сгенерируй короткий и чёткий вопрос на основе следующего текста. "
        f"Вопрос должен быть в одну строку:\n{fragment.page_content}"
    )

    client = _get_client()
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=0.3,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
    )

    question = response.choices[0].message.content.strip()
    if code_block:
        question = f"{question}{code_block}"
    return question


def generate_test_question(fragment: Document, num_choices: int) -> tuple[str, str]:
    """Generate a multiple-choice question. Returns (question_with_choices, correct_letter)."""
    system = f"""
        Ты — нейро-экзаменатор, который всегда чётко выполняет инструкции.
        Твоя задача — сгенерировать вопрос и ровно {num_choices} вариантов ответов
        на основе предоставленного текста.
        СТРОГО СОБЛЮДАЙ ФОРМАТ (без лишних отступов):

        ##_ Вопрос
        <текст вопроса>

        ##_ Варианты ответов
        А. <вариант>
        Б. <вариант>
        В. <вариант>
        Г. <вариант>

        ##_ Правильный ответ
        <буква>. <текст правильного ответа>

        Если в тексте есть код — ОБЯЗАТЕЛЬНО включи его в вопрос в формате:
        ```python
        # код
        ```

        Правильный ответ должен быть только один.
        Сделай так, чтобы правильный ответ не был постоянно под одной буквой.
    """

    code_match = re.search(
        r"```(?:python|sql|cpp|go)?\s*(.*?)\s*```", fragment.page_content, re.DOTALL
    )
    code_block = ""
    if code_match:
        code_block = f"```python\n{code_match.group(1).strip()}\n```\n\n"

    client = _get_client()
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=0.3,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    f"Сгенерируй вопрос и ровно {num_choices} вариантов ответов "
                    f"на основе данного текста: {fragment.page_content}, "
                    f"а также укажи правильный вариант ответа."
                ),
            },
        ],
    )

    return _parse_test_response(response.choices[0].message.content.strip(), code_block)


# ── Topic-only generators (no document) ───────────────────────────────────────

def generate_open_question_no_doc(topic: str, subtopic: str) -> str:
    """Generate an open-ended question about a topic without a document."""
    system = """
    Ты — нейро-экзаменатор, специализирующийся на технических собеседованиях.
    Твоя задача — задать один конкретный открытый вопрос по заданной теме и подтеме.
    Вопрос должен быть:
    - Чётким и однозначным
    - Подходящим для технического собеседования
    - В одну-две строки
    - Без вариантов ответа

    Если уместно — добавь небольшой пример кода к вопросу.
    """

    user_prompt = (
        f"Тема: {topic}\n"
        f"Подтема: {subtopic}\n\n"
        f"Задай один открытый вопрос для технического собеседования по этой подтеме."
    )

    client = _get_client()
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=0.5,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content.strip()


def generate_test_question_no_doc(topic: str, subtopic: str, num_choices: int) -> tuple[str, str]:
    """Generate a multiple-choice question about a topic without a document."""
    system = f"""
        Ты — нейро-экзаменатор для технических собеседований.
        Сгенерируй вопрос и ровно {num_choices} вариантов ответов по теме.
        СТРОГО СОБЛЮДАЙ ФОРМАТ:

        ##_ Вопрос
        <текст вопроса>

        ##_ Варианты ответов
        А. <вариант>
        Б. <вариант>
        В. <вариант>
        Г. <вариант>

        ##_ Правильный ответ
        <буква>. <текст правильного ответа>

        Если уместно — добавь пример кода к вопросу.
        Правильный ответ должен быть только один.
        Остальные варианты должны быть правдоподобными, но неверными.
        Меняй букву правильного ответа — не всегда А.
    """

    client = _get_client()
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=0.5,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    f"Тема: {topic}\n"
                    f"Подтема: {subtopic}\n\n"
                    f"Сгенерируй вопрос с {num_choices} вариантами ответов "
                    f"для технического собеседования по этой подтеме."
                ),
            },
        ],
    )

    return _parse_test_response(response.choices[0].message.content.strip(), "")


# ── Response parser ────────────────────────────────────────────────────────────

def _parse_test_response(generated: str, code_block: str) -> tuple[str, str]:
    generated = "\n".join(line.strip() for line in generated.split("\n"))
    parts = [p.strip() for p in generated.split("##_") if p.strip()]

    if len(parts) < 3:
        raise ValueError(f"Неверный формат ответа от GPT: {parts}")

    question = parts[0].replace("Вопрос", "").strip().lstrip(":").strip()
    answers = parts[1].replace("Варианты ответов", "").strip().lstrip(":").strip()
    correct_full = parts[2].replace("Правильный ответ", "").strip()

    correct_match = re.search(r"([А-Г])\.\s*", correct_full)
    if not correct_match:
        raise ValueError(f"Не удалось определить правильный ответ: {correct_full}")
    correct_letter = correct_match.group(1)

    if code_block:
        question = f"{question}\n\nРассмотрите следующий код:\n{code_block}"

    full_message = f"{question}\n\n{answers}"
    return full_message, correct_letter
