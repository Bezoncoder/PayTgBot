from pprint import pprint
from github import Github
import requests
import os
import github3

# Client ID
# Ov23liSqhkZegg27aQBe
# Secret key
#
# Classik !!!
#

# GITHUB_TOKEN =
# OWNER = "halltape"
# REPO = "InfraSharing"
# USERNAME = "Bezoncoder"


# https://api.github.com/repos/OWNER/REPO/collaborators/USERNAME
# url = "https://api.github.com/repos/OWNER/REPO/collaborators/USERNAME"
# headers = {
#     "Accept": "application/vnd.github+json",
#     "Authorization": "Bearer <YOUR-TOKEN>",
#     "X-GitHub-Api-Version": "2022-11-28"
# }
#
# response = requests.get(url, headers=headers)
# print(response.json())


def add_user(username):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/collaborators/{username}"
    r = requests.put(url, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    })
    return r.json()


def remove_user(username):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/collaborators/{username}"
    r = requests.delete(url, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    })
    return r.status_code


# pip install github3.py

if __name__ == "__main__":

    gh = github3.login(token=GITHUB_TOKEN)

    # Укажите имя пользователя и название репозитория
    owner = OWNER
    repo_name = REPO
    username_to_add = USERNAME

    # Получите объект репозитория
    repo = gh.repository(owner, repo_name)

    # Добавьте соавтора
    if repo:
        # Проверьте, что пользователь уже не добавлен
        # repo.is_collaborator(username_to_add) можно использовать для проверки
        if repo.add_collaborator(username_to_add):
            print(f"Пользователь {username_to_add} успешно добавлен в репозиторий {repo_name}")
        else:
            print(f"Ошибка добавления пользователя {username_to_add} в репозиторий {repo_name}")
    else:
        print(f"Репозиторий {repo_name} не найден.")
