import email
from configparser import ConfigParser
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Any

from rspamd_learn import get_imap


def list_mails(folder: str, config_file: str):
    # type: ignore
    def get_header_field(msg: Any, field: str) -> str | None:
        value = msg.get(field)
        if value is None:
            return None
        return decode_header(header=value)[0][0]

    config = ConfigParser()
    config.read(filenames=config_file)

    last_days = config.getint(
        section="DEFAULT",
        option="LAST_DAYS",
        fallback=0,
    )

    imap = get_imap(config)

    # folders = imap.get_folders("")
    # print(folders)

    search_filter: list[str] = ["(NOT DELETED)"]
    # search_filter_list: list[str] = ["DELETED"]
    if last_days:
        max_age = (
            datetime.now() - timedelta(days=last_days)
        ).strftime('%d-%b-%Y')
        search_filter.extend(('SINCE', max_age))

    mails: list[tuple[str, datetime | None, str |
                      None, str | None, str | None]] = []
    for mail in imap.get_mails(folder=folder, imap_search_filter=search_filter, header_only=True):
        msg = email.message_from_bytes(mail[1])

        # Extract headers
        email_from = get_header_field(msg, 'From')
        email_to = get_header_field(msg, 'To')
        email_date = parsedate_to_datetime(get_header_field(msg, 'Date'))
        email_message_id = get_header_field(msg, 'Message-ID')

        mails.append((mail[0][1], email_date, email_from,
                     email_to, email_message_id))

    mails.sort(key=lambda m: m[1], reverse=True)  # type: ignore

    for mail in mails:
        # Print the headers
        flags, email_date, email_from, email_to, email_message_id = mail
        print(flags, email_date.isoformat() if email_date else email_date,
              email_from, email_to, email_message_id)

    print("Total mails", len(mails))


if __name__ == "__main__":
    list_mails(folder="public/runlevel3", config_file="config.ini")
