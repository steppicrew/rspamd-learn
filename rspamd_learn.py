import re
from configparser import ConfigParser
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Generator, Iterable, Literal, Union

from lib.db import DB
from lib.imap import IMAP
from lib.rspam import RSpam

MailStatusType = Union[Literal["S"], Literal["H"]]


def get_verbosity(config: ConfigParser):
    return config.getint(
        section="DEFAULT",
        option="VERBOSITY",
        fallback=0,
    )


def get_imap(config: ConfigParser) -> IMAP:
    return IMAP(
        host=config.get("IMAP", "HOST"),
        username=config.get("IMAP", "USER"),
        password=config.get("IMAP", "PASSWORD"),
        port=int(config.get("IMAP", "PORT")),
        security=config.get("IMAP", "SECURITY") or None,  # type:ignore
    )


def get_mails(config: ConfigParser, db: DB, folders: set[str], mail_status: MailStatusType, imap_search_filter: Iterable[str] | None) -> Generator[tuple[bool | None, bytes], None, None]:

    update_db = config.getboolean(
        section="DEFAULT",
        option="WRITE_TO_DB",
        fallback=True,
    )
    verbosity = get_verbosity(config)

    def search_filter(flags: bytes, mail_header: bytes) -> tuple[None | bool, str]:
        mail_sha = sha256(mail_header).hexdigest()
        old_status = db.get(mail_sha)
        if old_status is None:
            return (True, mail_sha)
        if old_status == mail_status:
            return (False, mail_sha)

        if b'\\Deleted' in flags:
            print(mail_sha, old_status, mail_status)
            print(flags)
        return (None, mail_sha)

    imap: IMAP = get_imap(config)
    try:
        for folder in folders:
            count = 0
            try:
                for ((filter_result, mail_sha), mail_body) in imap.get_mails(folder, imap_search_filter=imap_search_filter, search_filter=search_filter):
                    if verbosity and count == 0:
                        print(f"Start scanning folder {folder} {mail_status}")

                    count += 1
                    try:
                        if verbosity > 1:
                            print(
                                f"Yielding mail {mail_sha} as {mail_status} (Filter result: {filter_result})"
                            )

                        yield (filter_result, mail_body)

                        if update_db:
                            try:
                                db.add(mail_sha, mail_status)
                            except Exception as exception:  # pylint:disable=[broad-exception-caught]
                                print("Error insering mail into db",
                                      repr(exception))

                    except Exception as exception:  # pylint:disable=[broad-exception-caught]
                        print("Error during yield", repr(exception))

            except Exception as exception:  # pylint:disable=[broad-exception-caught]
                print(
                    f"Error fetching mails ({folder} as {mail_status})",
                    repr(exception)
                )
                raise (exception)

            if verbosity and count:
                print(f"Ended scanning folder {folder} {mail_status}: {count}")
    finally:
        imap.logout()


def main(config_file: str):

    config = ConfigParser()
    config.read(filenames=config_file)

    verbosity = get_verbosity(config)

    imap = get_imap(config=config)

    db = DB(db_file=config.get(section="DEFAULT", option="SEEN_DB"))

    folders = imap.get_folders("")

    re_spam = r'(?:' + config.get(
        section="DEFAULT",
        option="SPAM_FOLDERS",
        fallback=r'(spam|junk)'  # default spam folders
    ) + r')$'
    spam_folders = set(
        folder
        for folder in folders
        if re.search(re_spam, folder, re.IGNORECASE)
    )

    re_ignore = r'(?:' + config.get(
        section="DEFAULT",
        option="IGNORE_FOLDERS",
        fallback=r'(inbox|sent)',  # ignore inbox by default
    ) + r')$'
    ham_folders = set(
        folder
        for folder in folders
        if folder not in spam_folders and not re.search(re_ignore, folder, re.IGNORECASE)
    )

    if verbosity > 1:
        print(f"Ham folders: {ham_folders}")
        print(f"Spam folders: {spam_folders}")

    rspam = RSpam(
        host=config.get("RSPAMD", "HOST"),
        do_train=config.getboolean(
            section="RSPAMD",
            option="TRAIN_RSPAMD",
            fallback=True,
        ),
    )

    last_days = config.getint(
        section="DEFAULT",
        option="LAST_DAYS",
        fallback=0,
    )

    search_filter: list[str] = ["(NOT DELETED)"]
    if last_days:
        max_age = (
            datetime.now() - timedelta(days=last_days)
        ).strftime('%d-%b-%Y')
        search_filter.extend(('SINCE', max_age))
    # print(search_filter)

    if verbosity >= 2:
        print("ham_folders", ham_folders)
        print("spam_folders", spam_folders)

    count = 0
    for ham, spam in zip(
        get_mails(
            config=config,
            db=db,
            folders=ham_folders,
            mail_status="H",
            imap_search_filter=search_filter,
        ),
        get_mails(
            config=config,
            db=db,
            folders=spam_folders,
            mail_status="S",
            imap_search_filter=search_filter
        )
    ):
        rspam.learn_ham(
            mail=ham[1],
            relearn=ham[0] is None,
        )
        rspam.learn_spam(
            mail=spam[1],
            relearn=spam[0] is None,
        )
        count += 1
    print(f"{count} messages learned")


if __name__ == "__main__":
    main("config.ini")
