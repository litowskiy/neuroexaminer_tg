from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards.reply import nav_bar, choose_prof
from bot.states import UserState
from utils.logger import get_user_logger

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    logger = get_user_logger(message.from_user.id)
    logger.info(f"Пользователь {message.from_user.username} начал взаимодействие с ботом.")
    await state.clear()
    text = (
        "Привет! Я — бот, который поможет тебе в подготовке к экзаменам. "
        "Прямо во время экзамена я генерирую вопросы по выбранной тобой теме "
        "и проверяю их прямо как реальный преподаватель!"
    )
    await message.answer(text, reply_markup=nav_bar)


@router.message(F.text == "В чем смысл бота?")
async def show_description(message: Message, state: FSMContext) -> None:
    logger = get_user_logger(message.from_user.id)
    logger.info(f"Пользователь {message.from_user.username} запросил информацию о боте.")
    text = (
        "Часто бывает такое, что читать материал достаточно скучно. "
        "К тому же он плохо запоминается, а готовиться к тесту/собеседованию/экзамену нужно.\n\n"
        "Этот бот поможет в подготовке!\n"
        "В зависимости от выбора уровня сложности тебе будут предложены вопросы "
        "с необходимостью написать ответ самому или с выбором ответа.\n"
        "Каждый раз, когда ты запускаешь экзаменатор, бот в режиме реального времени создаёт вопросы. "
        "После окончания экзамена он оценит их полноту и правильность прямо как настоящий преподаватель!\n\n"
        "Попробуй как это работает на уже доступных темах прямо сейчас!"
    )
    await message.answer(text, reply_markup=nav_bar)
    await state.set_state(UserState.choosing_topic)


@router.message(F.text == "Помощь")
async def show_help(message: Message, state: FSMContext) -> None:
    logger = get_user_logger(message.from_user.id)
    logger.info(f"Пользователь {message.from_user.username} запросил помощь.")
    text = (
        '1. Для начала экзамена нажми кнопку "Выбрать тему для подготовки", '
        "после чего тебе будут предложены темы для подготовки.\n\n"
        "2. Выбираешь сложность (Тесты или вопросы открытого типа)\n\n"
        "3. Выбираешь количество вариантов ответа, если ты выбрал тест, "
        "если нет — сразу переходишь к выбору количества вопросов\n\n"
        "4. Запускаешь экзамен и бустишь эффективность своей подготовки!"
    )
    await message.answer(text, reply_markup=nav_bar)
    await state.set_state(UserState.choosing_topic)


@router.message(F.text == "Выбрать тему для подготовки")
async def show_topic_menu(message: Message, state: FSMContext) -> None:
    logger = get_user_logger(message.from_user.id)
    logger.info(f"Пользователь {message.from_user.username} открыл меню выбора темы.")
    await message.answer("Выбирай тему:", reply_markup=choose_prof)
    await state.set_state(UserState.choosing_topic)


