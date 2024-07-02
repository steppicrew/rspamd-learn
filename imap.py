import imaplib
import re
import ssl
from typing import Generator, Literal

TypeSecurity = Literal["SSL", "TLS"]


class IMAP:
    def __init__(self, host: str, username: str, password: str, port: int | None = None, security: TypeSecurity | None = None) -> None:
        if port is None:
            if security is None:
                port = 993
                security = "SSL"
            else:
                port = 993 if security == "SSL" else 143
        else:
            if security is None:
                security = "TLS" if port == 143 else "SSL" if port == 993 else None

        if security == "SSL":
            self.imap = imaplib.IMAP4_SSL(host=host, port=port)
        else:
            self.imap = imaplib.IMAP4(host=host, port=port)
            if security == "TLS":
                self.imap.starttls(ssl.create_default_context())
        self.imap.login(user=username, password=password)

    def __del__(self):
        self.imap.logout()

    def select(self, mailbox: str):
        return self.imap.select(mailbox=mailbox)

    def get_folders(self, folder: str) -> list[str]:

        def parse_folders(folders: list[bytes]) -> list[str]:
            return [
                re.sub(
                    pattern=r'^\(\S+\) "[^"]+" (?:(?:"(.*)")|(\S+))$',
                    repl="\\1\\2",
                    string=folder.decode(encoding="UTF-8").strip()
                )
                for folder in folders
                if folder
            ]

        # always quote the folder name
        result, data = self.imap.list(directory=f'"{folder}"')
        if result != "OK":
            raise RuntimeError("Error listing folders", data)

        return parse_folders(data)  # type:ignore

    def get_mails(self, folder: str, search_filter: str | None = None) -> Generator[bytes, None, None]:
        self.imap.select(folder)
        result, data = self.imap.search(
            None, 'ALL' if search_filter is None else search_filter)
        if result != "OK":
            raise RuntimeError("Error getting mails for folder", folder, data)

        mail_ids = bytes(data[0]).decode(encoding="UTF-8").split()

        for mail_id in mail_ids:
            result, data = self.imap.fetch(mail_id, '(RFC822)')
            if result == "OK":
                yield data[0][1]  # type:ignore

        self.imap.close()
