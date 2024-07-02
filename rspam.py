from subprocess import run


class RSpam:
    def __init__(self, host: str):
        self.host = host

    def _run(self, *params: str, stdin: bytes | None = None, file: str | None = None):
        assert stdin is not None or file is not None
        assert stdin is None or file is None

        result = run(
            args=(
                "rspamc", "--connect", self.host, *params,
                *(tuple() if file is None else (file,))
            ),
            input=stdin,
            capture_output=True,
            check=False,
        )
        print("STDOUT", result.stdout)
        print("STDERR", result.stderr)
        return result.returncode

    def learn_spam(self, mail: bytes):
        return self._run("learn_spam", stdin=mail)

    def learn_ham(self, mail: bytes):
        return self._run("learn_ham", stdin=mail)
