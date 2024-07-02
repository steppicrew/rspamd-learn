import re
from configparser import ConfigParser
from datetime import datetime, timedelta
from hashlib import sha256

from db import DB
from imap import IMAP
from rspam import RSpam


def get_imap(config: ConfigParser):
    return IMAP(
        host=config.get("IMAP", "HOST"),
        username=config.get("IMAP", "USER"),
        password=config.get("IMAP", "PASSWORD"),
        port=int(config.get("IMAP", "PORT")),
        security=config.get("IMAP", "SECURITY") or None,  # type:ignore
    )


def get_mails(imap: IMAP, db: DB, folders: set[str], search_filter: str | None):
    for folder in folders:
        for mail in imap.get_mails(folder, search_filter):
            mail_sha = sha256(mail).hexdigest()
            if not db.has(mail_sha):
                yield mail
                db.add(mail_sha)


def main(config_file: str):

    config = ConfigParser()
    config.read(config_file)

    imap = get_imap(config)

    db = DB(config.get("DEFAULT", "SEEN_DB"))

    folders = imap.get_folders("")

    re_spam = config.get("DEFAULT", "SPAM_FOLDERS") + r'$'
    spam_folders = set(
        folder
        for folder in folders
        if re.search(re_spam, folder, re.IGNORECASE)
    )

    re_ignore = config.get("DEFAULT", "IGNORE_FOLDERS") + r'$'
    ham_folders = set(
        folder
        for folder in folders
        if folder not in spam_folders and not re.search(re_ignore, folder, re.IGNORECASE)
    )

    rspam = RSpam(host=config.get("RSPAMD", "HOST"))

    last_days = int(config.get("DEFAULT", "LAST_DAYS"))

    one_month_ago = (
        datetime.now() - timedelta(days=last_days)
    ).strftime('%d-%b-%Y')
    search_filter = f'SINCE "{one_month_ago}"'
    # search_filter = "DELETED"

    for ham, spam in zip(
        get_mails(
            imap=get_imap(config),
            db=db,
            folders=ham_folders,
            search_filter=search_filter,
        ),
        get_mails(
            imap=get_imap(config),
            db=db,
            folders=spam_folders,
            search_filter=search_filter
        )
    ):
        rspam.learn_ham(ham)
        rspam.learn_spam(spam)


if __name__ == "__main__":
    main("config.ini")
