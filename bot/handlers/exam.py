"""
Exam flow handlers.

FSM exam_data stored in state has the shape:
{
    "fragments":        list[dict],   # serialized Document objects (page_content + metadata)
                                      # OR list of {"topic": str, "subtopic": str} for no-doc mode
    "current_index":    int,
    "questions":        list[str],
    "student_answers":  list[str],
    "correct_answers":  list[str],    # only for test mode
    "mode":             "test" | "open",
    "no_doc":           bool,         # True when generating from GPT topic knowledge
    "user_score":       int,
    "total_score":      int,
    "num_variants":     int | None,   # test mode only
}
"""

import asyncio
import random
from concurrent.futures import ThreadPoolExecutor

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards.reply import (
    choose_lvl,
    nums_questions,
    vars_keyboard,
    nav_bar,
    remove_kb,
    create_answer_keyboard,
)
from bot.states import UserState
from config import settings
from services.answer_verifier import verify_open_answer, verify_test_answers
from services.document_loader import load_document_text, split_markdown_into_topics
from services.question_generator import (
    generate_open_question,
    generate_test_question,
    generate_open_question_no_doc,
    generate_test_question_no_doc,
    TOPIC_SUBTOPICS,
)
from utils.logger import get_user_logger

router = Router()
_executor = ThreadPoolExecutor()

# Темы с документом (URL) или без (None → GPT-only режим)
TOPICS: dict[str, str | None] = {
    "🐍 Python":              settings.PYTHON_DEV_DOC_URL or None,
    "⚙️ C++":                None,
    "🐹 Go":                  None,
    "🗄️ SQL":                None,
    "📊 Аналитика данных":   None,
}

# Внутренние названия тем для подбора подтем (без эмодзи)
TOPIC_DISPLAY_NAMES: dict[str, str] = {
    "🐍 Python":             "Python",
    "⚙️ C++":               "C++",
    "🐹 Go":                 "Go",
    "🗄️ SQL":               "SQL",
    "📊 Аналитика данных":  "Аналитика данных",
}

# Обратная совместимость — старые названия кнопок до переименования
TOPIC_ALIASES: dict[str, str] = {
    "Python-разработчик": "🐍 Python",
    "Аналитик данных":    "📊 Аналитика данных",
}

ALL_TOPIC_NAMES = list(TOPICS.keys()) + list(TOPIC_ALIASES.keys())


# ── Helpers ───────────────────────────────────────────────────────────────────

def _doc_to_dict(doc) -> dict:
    return {"page_content": doc.page_content, "metadata": doc.metadata}


async def _run_sync(fn, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, fn, *args)


def _make_no_doc_fragments(topic: str, num_questions: int) -> list[dict]:
    """Pick random subtopics for the topic to use as question seeds."""
    subtopics = TOPIC_SUBTOPICS.get(topic, [f"Основы {topic}"] * num_questions)
    chosen = random.sample(subtopics, min(num_questions, len(subtopics)))
    # If fewer subtopics than questions, repeat with shuffle
    while len(chosen) < num_questions:
        extra = random.sample(subtopics, min(num_questions - len(chosen), len(subtopics)))
        chosen.extend(extra)
    return [{"topic": topic, "subtopic": st} for st in chosen[:num_questions]]


# ── Topic ─────────────────────────────────────────────────────────────────────

@router.message(
    F.text.in_(ALL_TOPIC_NAMES),
    UserState.choosing_topic,
)
async def choose_topic(message: Message, state: FSMContext) -> None:
    logger = get_user_logger(message.from_user.id)
    # Нормализуем старые названия кнопок в новые
    topic = TOPIC_ALIASES.get(message.text, message.text)
    logger.info(f"Пользователь {message.from_user.username} выбрал тему '{topic}'.")
    await state.update_data(topic=topic)
    await message.answer("Отлично! Теперь выбери сложность:", reply_markup=choose_lvl)
    await state.set_state(UserState.choosing_difficulty)


# ── Difficulty ────────────────────────────────────────────────────────────────

@router.message(
    F.text.in_(["Тест (Легкий)", "Открытые вопросы (Сложный)"]),
    UserState.choosing_difficulty,
)
async def choose_difficulty(message: Message, state: FSMContext) -> None:
    logger = get_user_logger(message.from_user.id)
    logger.info(f"Пользователь {message.from_user.username} выбрал сложность: {message.text}.")
    await state.update_data(difficulty=message.text)
    await message.answer("Теперь выбери количество вопросов:", reply_markup=nums_questions)
    await state.set_state(UserState.choosing_num_q)


# ── Number of questions ───────────────────────────────────────────────────────

@router.message(F.text.in_(["3", "5", "15"]), UserState.choosing_num_q)
async def choose_num_questions(message: Message, state: FSMContext) -> None:
    logger = get_user_logger(message.from_user.id)
    logger.info(f"Пользователь {message.from_user.username} выбрал количество вопросов: {message.text}.")
    await state.update_data(num_questions=int(message.text))
    data = await state.get_data()

    if data["difficulty"] == "Тест (Легкий)":
        await message.answer("Теперь выбери количество вариантов ответов:", reply_markup=vars_keyboard)
        await state.set_state(UserState.choosing_num_v)
    else:
        await message.answer(
            f"Ты выбрал тему: {data['topic']}, сложность: {data['difficulty']}, "
            f"количество вопросов: {data['num_questions']}. Начинаем экзамен!",
            reply_markup=remove_kb,
        )
        await _start_exam(message, state)


# ── Number of variants ────────────────────────────────────────────────────────

@router.message(F.text.in_(["2", "3", "4"]), UserState.choosing_num_v)
async def choose_variants(message: Message, state: FSMContext) -> None:
    logger = get_user_logger(message.from_user.id)
    logger.info(f"Пользователь {message.from_user.username} выбрал количество вариантов: {message.text}.")
    await state.update_data(num_variants=int(message.text))
    data = await state.get_data()
    await message.answer(
        f"Ты выбрал тему: {data['topic']}, сложность: {data['difficulty']}, "
        f"количество вопросов: {data['num_questions']}, "
        f"количество вариантов: {data['num_variants']}. Начинаем экзамен!",
        reply_markup=remove_kb,
    )
    await state.set_state(UserState.taking_exam)
    await _start_exam(message, state)


# ── Exam start ────────────────────────────────────────────────────────────────

async def _start_exam(message: Message, state: FSMContext) -> None:
    logger = get_user_logger(message.from_user.id)
    data = await state.get_data()
    topic: str = data["topic"]
    difficulty: str = data["difficulty"]
    num_questions: int = data["num_questions"]
    num_variants: int | None = data.get("num_variants")

    doc_url = TOPICS.get(topic)
    mode = "test" if difficulty == "Тест (Легкий)" else "open"

    # ── No-document mode (GPT topic knowledge) ──────────────────────────────
    if not doc_url:
        display_name = TOPIC_DISPLAY_NAMES.get(topic, topic)
        fragments = _make_no_doc_fragments(display_name, num_questions)
        exam_data = {
            "fragments": fragments,
            "current_index": 0,
            "questions": [],
            "student_answers": [],
            "correct_answers": [],
            "mode": mode,
            "no_doc": True,
            "user_score": 0,
            "total_score": num_questions if mode == "test" else 0,
            "num_variants": num_variants,
        }
        await state.update_data(exam_data=exam_data)
        await state.set_state(UserState.taking_exam)
        await _ask_next_question(message, state)
        return

    # ── Document mode ────────────────────────────────────────────────────────
    await message.answer("Загружаю материал, это может занять несколько секунд…")
    try:
        document_text = await _run_sync(load_document_text, doc_url)
        fragments_docs = await _run_sync(split_markdown_into_topics, document_text, num_questions)
        fragments = [_doc_to_dict(f) for f in fragments_docs]
    except Exception as e:
        logger.error(f"Ошибка загрузки документа: {e}")
        await message.answer("Не удалось загрузить материал. Попробуй позже.")
        return

    exam_data = {
        "fragments": fragments,
        "current_index": 0,
        "questions": [],
        "student_answers": [],
        "correct_answers": [],
        "mode": mode,
        "no_doc": False,
        "user_score": 0,
        "total_score": num_questions if mode == "test" else 0,
        "num_variants": num_variants,
    }
    await state.update_data(exam_data=exam_data)
    await state.set_state(UserState.taking_exam)
    await _ask_next_question(message, state)


# ── Ask next question ─────────────────────────────────────────────────────────

async def _ask_next_question(message: Message, state: FSMContext) -> None:
    logger = get_user_logger(message.from_user.id)
    data = await state.get_data()
    exam_data: dict = data["exam_data"]

    if exam_data["current_index"] >= len(exam_data["fragments"]):
        await _grade_exam(message, state)
        return

    fragment = exam_data["fragments"][exam_data["current_index"]]
    no_doc: bool = exam_data.get("no_doc", False)

    await message.answer("Генерирую вопрос…")
    try:
        if no_doc:
            topic = fragment["topic"]
            subtopic = fragment["subtopic"]
            if exam_data["mode"] == "test":
                num_variants = exam_data["num_variants"]
                question, correct_letter = await _run_sync(
                    generate_test_question_no_doc, topic, subtopic, num_variants
                )
                exam_data["correct_answers"].append(correct_letter)
                kb = create_answer_keyboard(num_variants)
                await message.answer(question, reply_markup=kb)
            else:
                question = await _run_sync(generate_open_question_no_doc, topic, subtopic)
                await message.answer(question)
        else:
            class _Fragment:
                def __init__(self, d):
                    self.page_content = d["page_content"]
                    self.metadata = d["metadata"]

            frag_obj = _Fragment(fragment)
            if exam_data["mode"] == "test":
                num_variants = exam_data["num_variants"]
                question, correct_letter = await _run_sync(
                    generate_test_question, frag_obj, num_variants
                )
                exam_data["correct_answers"].append(correct_letter)
                kb = create_answer_keyboard(num_variants)
                await message.answer(question, reply_markup=kb)
            else:
                question = await _run_sync(generate_open_question, frag_obj)
                await message.answer(question)

    except Exception as e:
        logger.error(f"Ошибка генерации вопроса: {e}")
        await message.answer("Не удалось сгенерировать вопрос. Пропускаю...")
        question = "[ошибка генерации]"
        if exam_data["mode"] == "test":
            exam_data["correct_answers"].append("А")

    exam_data["questions"].append(question)
    logger.info(f"Бот задал вопрос: {question[:80]}…")
    await state.update_data(exam_data=exam_data)


# ── Receive answer ────────────────────────────────────────────────────────────

@router.message(UserState.taking_exam)
async def receive_answer(message: Message, state: FSMContext) -> None:
    logger = get_user_logger(message.from_user.id)
    logger.info(f"Пользователь {message.from_user.username} ответил: {message.text}")
    data = await state.get_data()
    exam_data: dict = data["exam_data"]

    exam_data["student_answers"].append(message.text)
    exam_data["current_index"] += 1
    await state.update_data(exam_data=exam_data)
    await _ask_next_question(message, state)


# ── Grade exam ────────────────────────────────────────────────────────────────

async def _grade_exam(message: Message, state: FSMContext) -> None:
    logger = get_user_logger(message.from_user.id)
    logger.info(f"Пользователь {message.from_user.id} завершил экзамен.")
    data = await state.get_data()
    exam_data: dict = data["exam_data"]
    num_questions: int = data["num_questions"]

    feedback_lines: list[str] = []

    if exam_data["mode"] == "test":
        verify_test_answers(exam_data)
        score = exam_data["user_score"]
        total = exam_data["total_score"]
        pct = round(score / total * 100, 2) if total else 0

        if pct < 40:
            comment = "Не мешало бы ещё поготовиться!"
        elif pct < 60:
            comment = "Неплохо! Но надо ещё поготовиться!"
        elif pct < 80:
            comment = "Хорошо! Ещё немного и будешь знать лучше, чем я! Продолжай в том же духе!"
        else:
            comment = "Ты отлично знаешь материал! Так держать!"

        feedback_lines.append(
            f"Ты решил правильно {score} из {total}.\n"
            f"Процент правильных: {pct}%\n\n{comment}"
        )
    else:
        await message.answer("Проверяю твои ответы, это займёт немного времени…")
        for i, (fragment, question, answer) in enumerate(
            zip(exam_data["fragments"], exam_data["questions"], exam_data["student_answers"]),
            start=1,
        ):
            # Для no_doc режима передаём объединённый контекст
            if exam_data.get("no_doc"):
                context = f"Тема: {fragment['topic']}\nПодтема: {fragment['subtopic']}"
            else:
                context = fragment["page_content"]

            try:
                grade, explanation = await _run_sync(
                    verify_open_answer, context, question, answer
                )
                exam_data["total_score"] += int(grade)
            except Exception as e:
                logger.error(f"Ошибка проверки ответа {i}: {e}")
                grade, explanation = "?", "Ошибка проверки"
            feedback_lines.append(f"Вопрос {i}:\nОценка: {grade}\nПояснение: {explanation}")

        max_score = 5 * num_questions
        feedback_lines.append(f"Твой балл за экзамен: {exam_data['total_score']} / {max_score}")

    final_response = "\n\n".join(feedback_lines)
    logger.info(f"Результаты: {final_response[:200]}")
    await message.answer(final_response, reply_markup=nav_bar)
    await state.clear()
