import imaplib
import re
import ssl
from typing import Callable, Generator, Iterable, Literal

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
        (result, _) = self.imap.login(user=username, password=password)

        if result != "OK":
            raise RuntimeError("Could not login to IMAP server")

        self.logged_in = True
        self.selected = False

    def __del__(self):
        self.logout()

    def close(self):
        if self.selected:
            try:
                self.imap.close()
            except:  # pylint:disable=[bare-except]
                pass
            self.selected = False

    def logout(self):
        self.close()

        if self.logged_in:
            try:
                self.imap.logout()
            except:  # pylint:disable=[bare-except]
                pass
            self.logged_in = False

    def select(self, mailbox: str):
        self.close()
        result = self.imap.select(mailbox=mailbox)
        self.selected = result[0] == "OK"
        return result

    def get_folders(self, folder: str) -> list[str]:
        assert self.logged_in

        def parse_folders(folders: list[bytes]) -> list[str]:
            return [
                re.sub(
                    pattern=r'^\([^\)]+\) "[^"]+" (?:(?:"(.*)")|(\S+))$',
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

    def get_mail(self, mail_id: str, header_only: bool = False) -> tuple[bytes, bytes] | None:
        if not self.logged_in:
            raise RuntimeError("get_mail() not logged in")
        if not self.selected:
            raise RuntimeError("get_mail() nothing selected")

        message_parts = "(FLAGS RFC822.HEADER)" if header_only else "(RFC822)"
        result, mail_data = self.imap.fetch(
            message_set=mail_id,
            message_parts=message_parts,
        )

        if result == 'OK' and isinstance(mail_data[0], tuple):
            return mail_data[0]  # type:ignore

    def get_mails(self, folder: str, imap_search_filter: Iterable[str] | None = None, search_filter: Callable[[bytes, bytes], tuple[bool | None, str]] | None = None, header_only: bool = False) -> Generator[tuple[tuple[bool | None, str], bytes], None, None]:
        if not imap_search_filter:
            imap_search_filter = ('ALL')
        self.select(f'"{folder}"')
        if not self.selected:
            raise RuntimeError(f"Folder {folder} could not be selected")

        try:
            mail_header_result, data = self.imap.search(
                None,
                *imap_search_filter
            )
        except Exception as e:  # pylint:disable=[broad-exception-caught]
            print(f"Error reading mails in folder '{folder}'", repr(e))
            return
            # raise e

        if mail_header_result != "OK":
            raise RuntimeError("Error getting mails for folder", folder, data)

        mail_ids = bytes(data[0]).decode(encoding="UTF-8").split()

        for mail_id in mail_ids:
            if not self.selected:
                raise RuntimeError(f"Folder {folder} is not selected")

            if header_only:
                header = self.get_mail(mail_id=mail_id, header_only=True)
                if header is None:
                    continue

                yield ((True, header[0].decode("UTF-8")), header[1])
                continue

            elif search_filter is not None:
                header = self.get_mail(mail_id=mail_id, header_only=True)
                if header is None:
                    continue

                filter_result = search_filter(*header)
                if filter_result[0] is False:
                    continue
            else:
                filter_result = (True, "")

            body = self.get_mail(mail_id)
            if body is not None:
                yield (filter_result, body[1])

        self.imap.close()
