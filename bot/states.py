from aiogram.fsm.state import State, StatesGroup


class UserState(StatesGroup):
    choosing_topic = State()
    choosing_difficulty = State()
    choosing_num_q = State()
    choosing_num_v = State()
    taking_exam = State()


class MaterialState(StatesGroup):
    viewing_menu = State()       # главное меню базы знаний
    waiting_for_file = State()   # ожидаем файл или текст от пользователя
    naming_material = State()    # ожидаем название материала
    viewing_list = State()       # список материалов
    material_selected = State()  # материал выбран, показываем действия
