# 2722037960

import os


async def get_subscribe_link() -> str:
    if os.getenv("INFRASHARING_CHAT_LINK"):
        link = os.getenv("INFRASHARING_CHAT_LINK")
    else:
        link = "INFRASHARING_CHAT_LINK"
    return link
