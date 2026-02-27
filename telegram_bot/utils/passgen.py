import string
import random


def get_password(pass_len: int) -> str:
    pull_of_char = string.digits + string.ascii_letters
    password = ''
    for i in range(pass_len):
        char = random.choice(pull_of_char)
        password += char
    return password


if __name__ == "__main__":
    print(get_password(8))
