from __future__ import annotations


class PrAuditError(Exception):
    """Base error for recoverable CLI failures."""


class InvalidGitRefError(PrAuditError):
    def __init__(self, ref: str, message: str | None = None) -> None:
        self.ref = ref
        super().__init__(message or f"Invalid git ref: {ref}")


class GitCommandError(PrAuditError):
    def __init__(self, command: list[str], stderr: str | None = None) -> None:
        self.command = command
        self.stderr = stderr or ""
        super().__init__(self._format())

    def _format(self) -> str:
        joined = " ".join(self.command)
        if self.stderr:
            return f"git command failed: {joined}\n{self.stderr.strip()}"
        return f"git command failed: {joined}"


class OutputError(PrAuditError):
    pass
