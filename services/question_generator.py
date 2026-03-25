import re

import httpx
from openai import OpenAI
from langchain.docstore.document import Document

from config import settings


class _CustomHTTPClient(httpx.Client):
    def __init__(self, *args, **kwargs):
        kwargs.pop("proxies", None)
        super().__init__(*args, **kwargs)


def _get_client() -> OpenAI:
    return OpenAI(api_key=settings.OPENAI_API_KEY, http_client=_CustomHTTPClient())


def generate_open_question(fragment: Document) -> str:
    """Generate a single open-ended question from a document fragment."""
    headers = fragment.metadata
    topic_title = headers.get("Header 1", "Unknown Topic")
    question_title = headers.get("Header 2", "Unknown Question")

    system = """
    Ты - нейро-экзаменатор, который всегда четко выполняет инструкции.
    Твоя задача - сгенерировать открытый вопрос на основе предоставленного текста.
    Каждый вопрос должен быть коротким, конкретным и строго соответствовать сути текста.

    ВАЖНО:
    1. Если в тексте есть код - ОБЯЗАТЕЛЬНО включи его в ответ.
    2. Не задавай вопросы по коду, если его нет в ответе.
    3. Если задаешь вопрос по коду - обязательно покажи релевантный код.
    """

    code_match = re.search(
        r"```(?:python|sql)?\s*(.*?)\s*```", fragment.page_content, re.DOTALL
    )
    code_block = ""
    if code_match:
        lang = "sql" if ("SELECT" in code_match.group(1) or "FROM" in code_match.group(1)) else "python"
        code_block = f"\n\nРассмотрите следующий код:\n```{lang}\n{code_match.group(1).strip()}\n```"

    user_prompt = (
        f"Тема: {topic_title}\n"
        f"Вопрос из темы: {question_title}\n"
        f"Сгенерируй короткий и чёткий вопрос на основе следующего текста. "
        f"Вопрос должен быть в одну строку:\n{fragment.page_content}"
    )

    client = _get_client()
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=0.1,
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
        Ты - нейро-экзаменатор, который всегда четко выполняет инструкции. Твоя задача - сгенерировать вопрос и варианты ответов к этому вопросу на основе предоставленного тебе
        текста. СТРОГО СОБЛЮДАЙ ФОРМАТ ОТВЕТА БЕЗ ОТСТУПОВ И ВНИМАТЕЛЬНО СМОТРИ КОЛИЧЕСТВО ВАРИАНТОВ ОТВЕТОВ {num_choices}:

        ##_ Вопрос
        <текст вопроса>

        ##_ Варианты ответов
        А. <вариант>
        Б. <вариант>
        В. <вариант>
        Г. <вариант>

        ##_ Правильный ответ
        <буква>. <текст правильного ответа>

        Если в тексте есть код - ОБЯЗАТЕЛЬНО включи его в вопрос в формате:
        ```python
        # код из текста
        ```

        Правильный ответ должен быть только один. Остальные ответы должны быть неправильными.
        Сделай так, чтобы правильный ответ не был постоянно под одной буквой.
        ОБЯЗАТЕЛЬНО старайся задавать вопросы из разных разделов документа.
    """

    code_match = re.search(
        r"```(?:python)?\s*(.*?)\s*```", fragment.page_content, re.DOTALL
    )
    code_block = ""
    if code_match:
        code_block = f"```python\n{code_match.group(1).strip()}\n```\n\n"

    client = _get_client()
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=0.1,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    f"Сгенерируй вопрос и {num_choices} вариантов ответов на этот вопрос "
                    f"на основе данного текста: {fragment.page_content}, "
                    f"а также укажи правильный вариант ответа."
                ),
            },
        ],
    )

    generated = response.choices[0].message.content.strip()
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
