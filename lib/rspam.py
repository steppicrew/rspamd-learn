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
        return result.returncode, result.stdout.decode("UTF-8"), result.stderr.decode("UTF-8")

    def _learn(self, cmd: str, mail: bytes, relearn: bool = False) -> bool:
        if self.do_learn:
            returncode, stdout, _stderr = self._run(
                cmd, *(('--header', 'Learn-Type: bulk') if relearn else ()), stdin=mail)
            if returncode == 0 and stdout.find("\nsuccess = true;") >= 0:
                return True
            return False

        return True

    def learn_spam(self, mail: bytes, relearn: bool = False):
        """
        Learn message as SPAM

        Args:
            mail (bytes): Message to learn
            relearn (bool, optional): Relearn this message. Defaults to False.

        Returns:
            bool: successfully learned
        """
        return self._learn("learn_spam", mail, relearn)

    def learn_ham(self, mail: bytes, relearn: bool = False):
        """
        Learn message as HAM

        Args:
            mail (bytes): Message to learn
            relearn (bool, optional): Relearn this message. Defaults to False.

        Returns:
            bool: successfully learned
        """
        return self._learn("learn_ham", mail, relearn)
