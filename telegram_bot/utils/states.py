from aiogram.fsm.state import StatesGroup, State


class OrderPay(StatesGroup):
    send_email = State()
    send_check = State()
    check_git = State()
    check_fio = State()

