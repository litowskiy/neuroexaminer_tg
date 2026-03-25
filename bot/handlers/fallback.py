from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards.reply import nav_bar
from utils.logger import get_user_logger

router = Router()


@router.message()
async def fallback_handler(message: Message, state: FSMContext) -> None:
    """Ловит всё что не обработал ни один другой роутер.
    Подключается последним в main.py — поэтому не мешает остальным хэндлерам."""
    logger = get_user_logger(message.from_user.id)
    current_state = await state.get_state()
    logger.warning(
        f"Пользователь {message.from_user.username} прислал необработанное сообщение "
        f"'{message.text}' в состоянии {current_state}. Сброс."
    )
    await state.clear()
    await message.answer(
        "Что-то пошло не так или я не понял команду. Начнём сначала!",
        reply_markup=nav_bar,
    )
