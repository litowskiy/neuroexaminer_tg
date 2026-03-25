from aiogram.fsm.state import State, StatesGroup


class UserState(StatesGroup):
    choosing_topic = State()
    choosing_difficulty = State()
    choosing_num_q = State()
    choosing_num_v = State()
    taking_exam = State()
