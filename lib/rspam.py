from subprocess import run


class RSpam:
    def __init__(self, host: str, do_train: bool = True):
        self.host = host
        self.do_learn = do_train

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

    def _learn(self, cmd: str, mail: bytes, relearn: bool = False):
        if self.do_learn:
            return self._run(cmd, *(('--header', 'Learn-Type: bulk') if relearn else ()), stdin=mail)

        return 0

    def learn_spam(self, mail: bytes, relearn: bool = False):
        return self._learn("learn_spam", mail, relearn)

    def learn_ham(self, mail: bytes, relearn: bool = False):
        return self._learn("learn_ham", mail, relearn)
