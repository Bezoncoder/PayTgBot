from pprint import pprint
from typing import Any
from utils.plategaio import PlategaAPI
from settings.config import MERCHANT_ID, PLATEGA_SECRET_KEY




platega = PlategaAPI(MERCHANT_ID, PLATEGA_SECRET_KEY)

def get_payment_link_data(payment_method, amount) -> dict:

    payment_operation_data = platega.create_payment(payment_method=payment_method, amount=amount, description='test')

    payment_link_data: dict[str, Any] = {}
    if payment_operation_data:
        payment_link_data['operation_id_from_provider'] = payment_operation_data.get('transactionId', 'none')
        payment_link_data['payment_link'] = payment_operation_data.get('redirect', 'none')
    return payment_link_data


def check_payment_status(operation_id_from_provider: str):
    # 'APPROVED'
    operation_status = ''
    check_pay = platega.get_payment_status(transaction_id=operation_id_from_provider)
    if check_pay:
        if check_pay.get('status') == 'CONFIRMED':
            operation_status = 'APPROVED'
    else:
        operation_status = 'NOT_FOUND'

    return operation_status


if __name__ == "__main__":
    operation_id = '6102bc29-ee90-4646-a96b-a50be07632e9'
    ID = "a59ad34e-9f13-40ac-a19d-cd688fc40e501"

    status = check_payment_status(operation_id_from_provider="ae6c4033-baed-4616-af8f-b2268682c9d1")
    print()
    pprint(status)
