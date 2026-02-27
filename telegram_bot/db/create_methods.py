from sqlalchemy.ext.asyncio import AsyncSession
from database import connection
from models import User
from asyncio import run



@connection
async def create_user(telegram_id: str, username: str, session: AsyncSession) -> int:
    user = User(telegram_id=telegram_id, username=username)
    session.add(user)
    await session.commit()
    return user.id










if __name__=="__main__":

    new_user_id = run(create_user(telegram_id='1111111',
                                            username='Vasja'))

    print(f"Новый пользователь с идентификатором {new_user_id} создан")
