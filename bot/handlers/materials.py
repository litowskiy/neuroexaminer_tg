"""
Handlers for the user knowledge base:
  - Upload materials (PDF / DOCX / TXT / plain text)
  - Name and save materials
  - List, select, delete materials
  - Start an exam from a saved material
"""
import io
import traceback

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards.reply import (
    nav_bar,
    materials_menu_kb,
    material_actions_kb,
    choose_lvl,
    create_materials_list_keyboard,
)
from bot.states import UserState, MaterialState
from services.file_parser import parse_file
from services.knowledge_base import (
    save_material,
    list_materials,
    get_material,
    delete_material,
)
from utils.logger import get_user_logger

router = Router()

MAX_TEXT_CHARS = 50_000   # ~50 KB inline text limit
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB

_SUPPORTED_EXTS = ("pdf", "txt", "docx")


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _show_list(message: Message, state: FSMContext) -> None:
    """Show numbered list of user's materials."""
    materials = list_materials(message.from_user.id)

    if not materials:
        await state.set_state(MaterialState.viewing_menu)
        await message.answer(
            "📭 У тебя пока нет сохранённых материалов.\n\n"
            "Нажми *«📤 Загрузить материал»* чтобы добавить первый!",
            reply_markup=materials_menu_kb,
            parse_mode="Markdown",
        )
        return

    lines = []
    for i, m in enumerate(materials, 1):
        date = m["created_at"][:10]
        chars = m.get("char_count", len(m["text"]))
        lines.append(f"{i}. *{m['name']}*\n   _{chars:,} символов · добавлен {date}_")

    text = "📚 *Твои материалы:*\n\n" + "\n\n".join(lines) + "\n\nВыбери номер материала:"

    await state.update_data(materials_list=[m["id"] for m in materials])
    await state.set_state(MaterialState.viewing_list)
    await message.answer(
        text,
        reply_markup=create_materials_list_keyboard(len(materials)),
        parse_mode="Markdown",
    )


# ── Navigation buttons (no state filter — work from anywhere) ─────────────────

@router.message(F.text == "📚 Мои материалы")
async def open_materials_menu(message: Message, state: FSMContext) -> None:
    logger = get_user_logger(message.from_user.id)
    logger.info(f"Пользователь {message.from_user.username} открыл меню материалов.")
    await state.set_state(MaterialState.viewing_menu)
    await message.answer(
        "📚 *База знаний*\n\n"
        "Загружай свои материалы и проходи по ним экзамены. "
        "Поддерживаются файлы *PDF, TXT, DOCX* или обычный текст.",
        reply_markup=materials_menu_kb,
        parse_mode="Markdown",
    )


@router.message(F.text == "🏠 Главное меню")
async def back_to_main(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню:", reply_markup=nav_bar)


@router.message(F.text == "📤 Загрузить материал")
async def start_upload(message: Message, state: FSMContext) -> None:
    await state.set_state(MaterialState.waiting_for_file)
    await message.answer(
        "📤 *Загрузка материала*\n\n"
        "Отправь файл (*PDF, TXT или DOCX*) или просто вставь текст прямо в чат.\n\n"
        "⚠️ Максимальный размер файла — 10 МБ.\n"
        "Для отмены нажми *«🏠 Главное меню»*.",
        parse_mode="Markdown",
    )


@router.message(F.text == "📋 Список материалов")
async def show_materials_list(message: Message, state: FSMContext) -> None:
    await _show_list(message, state)


# ── Material selected actions ─────────────────────────────────────────────────

@router.message(F.text == "🎓 Начать экзамен", MaterialState.material_selected)
async def start_exam_from_material(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    material_id = data.get("selected_material_id")
    material = get_material(message.from_user.id, material_id)

    if not material:
        await message.answer("❌ Материал не найден. Попробуй загрузить снова.")
        await state.set_state(MaterialState.viewing_menu)
        await message.answer("Меню:", reply_markup=materials_menu_kb)
        return

    await state.update_data(
        topic="📖 Мой материал",
        custom_material_id=material_id,
        custom_material_name=material["name"],
    )
    await state.set_state(UserState.choosing_difficulty)
    await message.answer(
        f"🎓 Экзамен по материалу *«{material['name']}»*\n\n"
        f"Выбери сложность:",
        reply_markup=choose_lvl,
        parse_mode="Markdown",
    )


@router.message(F.text == "🗑️ Удалить материал", MaterialState.material_selected)
async def delete_selected_material(message: Message, state: FSMContext) -> None:
    logger = get_user_logger(message.from_user.id)
    data = await state.get_data()
    material_id = data.get("selected_material_id")

    if material_id:
        material = get_material(message.from_user.id, material_id)
        name = material["name"] if material else "материал"
        delete_material(message.from_user.id, material_id)
        logger.info(f"Пользователь {message.from_user.username} удалил материал: «{name}»")
        await message.answer(f"🗑️ Материал *«{name}»* удалён.", parse_mode="Markdown")

    await _show_list(message, state)


@router.message(F.text == "🔙 К списку материалов", MaterialState.material_selected)
async def back_to_list(message: Message, state: FSMContext) -> None:
    await _show_list(message, state)


# ── File upload ───────────────────────────────────────────────────────────────

@router.message(MaterialState.waiting_for_file, F.document)
async def receive_document(message: Message, state: FSMContext, bot: Bot) -> None:
    logger = get_user_logger(message.from_user.id)
    doc = message.document

    if doc.file_size > MAX_FILE_BYTES:
        await message.answer("❌ Файл слишком большой. Максимум 10 МБ.")
        return

    filename = doc.file_name or "file.txt"
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext not in _SUPPORTED_EXTS:
        await message.answer(
            f"❌ Формат *{ext}* не поддерживается.\n"
            "Отправь файл в формате PDF, TXT или DOCX.",
            parse_mode="Markdown",
        )
        return

    await message.answer("⏳ Читаю файл…")
    try:
        file = await bot.get_file(doc.file_id)
        buf = io.BytesIO()
        await bot.download_file(file.file_path, buf)
        text = parse_file(buf.getvalue(), filename)
    except Exception as e:
        logger.error(f"Ошибка парсинга файла: {e}\n{traceback.format_exc()}")
        await message.answer(f"❌ Не удалось прочитать файл: {e}")
        return

    text = text.strip()
    if len(text) < 50:
        await message.answer("❌ Файл слишком короткий или пустой. Загрузи другой.")
        return

    auto_name = filename.rsplit(".", 1)[0]  # filename without extension
    await state.update_data(pending_text=text, pending_name=auto_name)
    await state.set_state(MaterialState.naming_material)
    await message.answer(
        f"✅ Файл прочитан! *{len(text):,}* символов\n\n"
        f"Как назвать этот материал?\n"
        f"_(предложение: «{auto_name}»)_\n\n"
        f"Отправь название или /skip для автоимени.",
        parse_mode="Markdown",
    )


@router.message(MaterialState.waiting_for_file, F.text)
async def receive_text_material(message: Message, state: FSMContext) -> None:
    text = message.text.strip()

    if len(text) < 50:
        await message.answer(
            "❌ Текст слишком короткий (минимум 50 символов).\n"
            "Вставь больше текста или загрузи файл."
        )
        return

    if len(text) > MAX_TEXT_CHARS:
        await message.answer(
            f"❌ Текст слишком длинный (максимум {MAX_TEXT_CHARS:,} символов).\n"
            "Сократи его или загрузи как файл."
        )
        return

    auto_name = text[:30].strip().replace("\n", " ") + "…"
    await state.update_data(pending_text=text, pending_name=auto_name)
    await state.set_state(MaterialState.naming_material)
    await message.answer(
        f"✅ Текст получен! *{len(text):,}* символов\n\n"
        f"Как назвать этот материал?\n\n"
        f"Отправь название или /skip для автоимени.",
        parse_mode="Markdown",
    )


# ── Naming material ───────────────────────────────────────────────────────────

@router.message(MaterialState.naming_material)
async def name_material(message: Message, state: FSMContext) -> None:
    logger = get_user_logger(message.from_user.id)
    data = await state.get_data()
    text = data["pending_text"]

    if message.text == "/skip":
        name = data["pending_name"]
    else:
        name = message.text.strip()[:80]

    material = save_material(message.from_user.id, name, text)
    logger.info(
        f"Пользователь {message.from_user.username} сохранил материал: "
        f"«{name}» ({len(text):,} символов)"
    )

    await state.update_data(
        selected_material_id=material["id"],
        pending_text=None,
        pending_name=None,
    )
    await state.set_state(MaterialState.material_selected)
    await message.answer(
        f"✅ Материал *«{name}»* сохранён!\n\n"
        f"Хочешь сразу начать экзамен по нему?",
        reply_markup=material_actions_kb,
        parse_mode="Markdown",
    )


# ── Select material from numbered list ────────────────────────────────────────

@router.message(F.text.regexp(r"^\d+$"), MaterialState.viewing_list)
async def select_material_by_number(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    materials_list: list[str] = data.get("materials_list", [])
    idx = int(message.text) - 1

    if idx < 0 or idx >= len(materials_list):
        await message.answer(f"❌ Введи номер от 1 до {len(materials_list)}.")
        return

    material_id = materials_list[idx]
    material = get_material(message.from_user.id, material_id)
    if not material:
        await message.answer("❌ Материал не найден. Возможно, он был удалён.")
        await _show_list(message, state)
        return

    await state.update_data(selected_material_id=material_id)
    await state.set_state(MaterialState.material_selected)

    chars = material.get("char_count", len(material["text"]))
    date = material["created_at"][:10]
    await message.answer(
        f"📄 *{material['name']}*\n"
        f"_{chars:,} символов · добавлен {date}_\n\n"
        f"Что хочешь сделать?",
        reply_markup=material_actions_kb,
        parse_mode="Markdown",
    )
