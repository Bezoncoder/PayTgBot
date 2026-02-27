import asyncio
from pydantic import create_model
from sqlalchemy.ext.asyncio import AsyncSession
from db.dao import PaymentDAO, UserDAO
from db.database import connection
from db.schemas import PaymentPydantic, UserPydantic


@connection
async def update_payment_data(session: AsyncSession, payment_id, new_operation_id: str, new_status: str):
    ValueModel = create_model('ValueModel', operation_id=(str, ...), status=(str, ...))
    payment = await PaymentDAO.update_one_by_id(session=session,
                                                data_id=int(payment_id),
                                                values=ValueModel(operation_id=new_operation_id,
                                                                  status=new_status))
    return PaymentPydantic.model_validate(payment)


@connection
async def update_user_email(session: AsyncSession, user_id_from_db, new_email: str):
    UserModel = create_model('UserModel', mail_info=(str, ...))
    user = await UserDAO.update_one_by_id(session=session,
                                          data_id=int(user_id_from_db),
                                          values=UserModel(mail_info=new_email))
    return UserPydantic.model_validate(user)


if __name__ == "__main__":
    test = asyncio.run(update_payment_data(payment_id=5, new_operation_id='QWERTY', new_status="APROVE"))
    print(test)
