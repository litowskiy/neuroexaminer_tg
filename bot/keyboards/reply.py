from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

# ── Main navigation bar ───────────────────────────────────────────────────────
nav_bar = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Выбрать тему для подготовки")],
        [KeyboardButton(text="📚 Мои материалы")],
        [KeyboardButton(text="В чем смысл бота?"), KeyboardButton(text="Помощь")],
    ],
    resize_keyboard=True,
)

# ── Topic selection ───────────────────────────────────────────────────────────
choose_prof = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🐍 Python"), KeyboardButton(text="⚙️ C++")],
        [KeyboardButton(text="🐹 Go"),     KeyboardButton(text="🗄️ SQL")],
        [KeyboardButton(text="📊 Аналитика данных")],
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

# ── Materials: main menu ──────────────────────────────────────────────────────
materials_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📤 Загрузить материал")],
        [KeyboardButton(text="📋 Список материалов")],
        [KeyboardButton(text="🏠 Главное меню")],
    ],
    resize_keyboard=True,
)

# ── Materials: actions for a selected material ────────────────────────────────
material_actions_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎓 Начать экзамен")],
        [KeyboardButton(text="🗑️ Удалить материал")],
        [KeyboardButton(text="🔙 К списку материалов")],
        [KeyboardButton(text="🏠 Главное меню")],
    ],
    resize_keyboard=True,
)

remove_kb = ReplyKeyboardRemove()


def create_answer_keyboard(num_buttons: int) -> ReplyKeyboardMarkup:
    """Build a keyboard with Cyrillic letters А, Б, В … up to num_buttons."""
    buttons = [KeyboardButton(text=chr(ord("А") + i)) for i in range(num_buttons)]
    return ReplyKeyboardMarkup(keyboard=[buttons], resize_keyboard=True)


def create_materials_list_keyboard(count: int) -> ReplyKeyboardMarkup:
    """Keyboard with number buttons for selecting a material from the list."""
    buttons = [KeyboardButton(text=str(i + 1)) for i in range(count)]
    # Group into rows of 3
    rows = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    rows.append([KeyboardButton(text="🏠 Главное меню")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)
