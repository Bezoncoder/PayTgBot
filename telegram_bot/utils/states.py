from aiogram.fsm.state import StatesGroup, State


class OrderPay(StatesGroup):
    check_id_message = State()
    get_account_summary = State()
    send_email = State()
    send_check = State()
    check_git = State()
    check_fio = State()
    set_order = State()


