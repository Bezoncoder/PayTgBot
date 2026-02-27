import re
import requests
import logging


def parse_repo_url(repo_url: str) -> tuple[str, str] | None:
    """Return (owner, repo) from a github repo URL like https://github.com/owner/name."""
    if not repo_url:
        return None
    repo_url = repo_url.strip()
    match = re.search(r"github\.com[:/]+([^/]+)/([^/]+)", repo_url)
    if not match:
        return None
    owner = match.group(1)
    repo = match.group(2)
    repo = repo.split("?")[0].split("#")[0]
    repo = repo.rstrip("/")
    if repo.endswith(".git"):
        repo = repo[:-4]
    return owner, repo


class GitHubRepoManager:
    def __init__(self, token: str, owner: str, repo: str):
        # logging.info("Создан Экземпляр класса %s", self.__class__.__name__)
        self.token = token
        self.owner = owner
        self.repo = repo
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
            }
        )

    @staticmethod
    def extract_username(raw):
        # Если это ссылка, то вытаскивает username из URL, иначе возвращает как есть
        match = re.search(r"github\.com/([A-Za-z0-9_-]+)", raw)
        if match:
            return match.group(1)
        # Просто валидация: только буквы, цифры, минус, _
        username = re.sub(r"[^A-Za-z0-9_-]", "", raw)
        return username

    def check_user_exists(self, username):
        username = self.extract_username(username)
        # logging.info("▶ Check user: %s exists from Github ", username)
        url = f"https://api.github.com/users/{username}"
        response = self.session.get(url)
        status = response.status_code == 200
        # logging.info("▶ Check user exists Status  = %s", status)
        return status

    def get_list_collaborators(self):
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/collaborators"
        response = self.session.get(url)
        if response.status_code == 200:
            return [user["login"] for user in response.json()]
        return []

    def invite_user(self, username, permission="push"):
        username = self.extract_username(username)
        if not self.check_user_exists(username):
            logging.info("▶ User %s does not exist!", username)
            return
        if username in self.get_list_collaborators():
            logging.info("▶ User %s is already a collaborator.", username)
            return
        else:
            url = f"https://api.github.com/repos/{self.owner}/{self.repo}/collaborators/{username}"
            response = self.session.put(url, json={"permission": permission})
            if response.status_code in [201, 204]:
                logging.info("▶ Invitation sent to %s", username)
                invite_link = f"https://github.com/{self.owner}/{self.repo}/invitations"
                return invite_link
            else:
                logging.info("▶ Failed to invite: %s", response.json())
                return

    def remove_collaborator(self, username):
        username = self.extract_username(username)
        if not self.check_user_exists(username):
            # logging.info("▶ User %s does not exist!", username)
            return

        self.remove_user_invitations(username)
        collaborators = self.get_list_collaborators()
        username_lower = username.lower()
        collaborators_lower = {user.lower() for user in collaborators}

        if username_lower in collaborators_lower:
            username = self.extract_username(username)
            url = f"https://api.github.com/repos/{self.owner}/{self.repo}/collaborators/{username}"
            response = self.session.delete(url)
            if response.status_code == 204:
                logging.info("▶ Collaborator %s removed", username)
                return True
            else:
                logging.info("▶ Failed to remove: %s removed", response.json())
                return False
        # "Deleting Successfull!"

    def get_list_invitations(self):
        list_invitations = []
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/invitations"
        response = self.session.get(url)
        if response.status_code == 200:
            list_invitations = response.json()
        return list_invitations

    def remove_user_invitations(self, username):
        username = self.extract_username(username)
        invitations = self.get_list_invitations()
        for invite in invitations:
            if (
                    "invitee" in invite
                    and invite["invitee"]["login"].lower() == username.lower()
            ):
                url = f"https://api.github.com/repos/{self.owner}/{self.repo}/invitations/{invite['id']}"
                response = self.session.delete(url)
                if response.status_code == 204:
                    logging.info("▶ Invitation for %s removed", username)
                    return True
                else:
                    logging.info("▶ Failed to remove invitation: %s", response.json())
                    return False
        else:
            # logging.info("▶ No invitation found for: %s", username)
            return
