import asyncio
from pydantic import create_model
from sqlalchemy.ext.asyncio import AsyncSession
from db.dao import PaymentDAO, UserDAO, EnrollmentDAO, ReferralRewardsDAO
from db.database import connection
from db.schemas import PaymentPydantic, UserPydantic, EnrollmentPydantic, ReferralRewardsPydantic


@connection
async def update_payment_data(session: AsyncSession, payment_id, new_operation_id: str, new_status: str, stream_id: int = None):
    ValueModel = create_model('ValueModel', operation_id=(str, ...), status=(str, ...))
    payment = await PaymentDAO.update_one_by_id(session=session,
                                                data_id=int(payment_id),
                                                values=ValueModel(operation_id=new_operation_id,
                                                                  status=new_status,
                                                                  stream_id=stream_id))
    return PaymentPydantic.model_validate(payment)


@connection
async def update_user_email(session: AsyncSession, user_id_from_db, new_email: str):
    UserModel = create_model('UserModel', mail_info=(str, ...))
    user = await UserDAO.update_one_by_id(session=session,
                                          data_id=int(user_id_from_db),
                                          values=UserModel(mail_info=new_email))
    return UserPydantic.model_validate(user)

@connection
async def update_enrollment_data(session: AsyncSession, enrollment_id, new_active_status: bool):
    ValueModel = create_model('ValueModel', active=(bool, ...))
    enrollment = await EnrollmentDAO.update_one_by_id(session=session,
                                                data_id=int(enrollment_id),
                                                values=ValueModel(active=new_active_status))
    if enrollment:
        result = EnrollmentPydantic.model_validate(enrollment)
    else:
        result = None

    return result

@connection
async def update_referral_rewards(session: AsyncSession, user_id:int, values_dict: dict):
    referral_reward = await ReferralRewardsDAO.update_by_user_id(session=session, user_id=user_id, values=values_dict)
    if referral_reward:
        rez = ReferralRewardsPydantic.model_validate(referral_reward)
    else:
        rez = None
    return rez







if __name__ == "__main__":
    test = asyncio.run(update_payment_data(payment_id=5, new_operation_id='QWERTY', new_status="APROVE"))
    print(test)
