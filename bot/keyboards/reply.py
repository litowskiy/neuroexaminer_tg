from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

# ── Topic selection ───────────────────────────────────────────────────────────
choose_prof = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Python-разработчик")],
        [KeyboardButton(text="Аналитик данных")],
    ],
    resize_keyboard=True,
)

# ── Difficulty selection ──────────────────────────────────────────────────────
choose_lvl = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Тест (Легкий)")],
        [KeyboardButton(text="Открытые вопросы (Сложный)")],
    ],
    resize_keyboard=True,
)

# ── Main navigation bar ───────────────────────────────────────────────────────
nav_bar = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Выбрать тему для подготовки")],
        [KeyboardButton(text="В чем смысл бота?")],
        [KeyboardButton(text="Помощь")],
    ],
    resize_keyboard=True,
)

# ── Number of questions ───────────────────────────────────────────────────────
nums_questions = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="3"), KeyboardButton(text="5"), KeyboardButton(text="15")]],
    resize_keyboard=True,
)

# ── Number of answer choices ──────────────────────────────────────────────────
vars_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="2"), KeyboardButton(text="3"), KeyboardButton(text="4")]],
    resize_keyboard=True,
)

remove_kb = ReplyKeyboardRemove()


def create_answer_keyboard(num_buttons: int) -> ReplyKeyboardMarkup:
    """Build a keyboard with Cyrillic letters А, Б, В … up to num_buttons."""
    buttons = [KeyboardButton(text=chr(ord("А") + i)) for i in range(num_buttons)]
    return ReplyKeyboardMarkup(keyboard=[buttons], resize_keyboard=True)
