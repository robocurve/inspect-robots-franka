"""Injectable operator readiness and success confirmation for real runs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from inspect_robots.errors import EmbodimentFault

_AFFIRMATIVE = frozenset({"y", "yes", "1", "true", "success", "pass"})


@dataclass
class OperatorIO:
    """Console I/O isolated behind injectable callables."""

    input_fn: Callable[[str], str] = input
    output_fn: Callable[[str], None] = print

    def wait_ready(self, prompt: str = "Position the scene, then press Enter to start...") -> None:
        """Block for readiness or turn dead stdin into a halting hardware fault."""
        try:
            self.input_fn(prompt)
        except (EOFError, OSError) as exc:
            raise EmbodimentFault(
                "operator readiness prompt could not read stdin (no interactive "
                "terminal?). Run from a real TTY, inject an OperatorIO with a "
                "working input_fn, or set FrankaConfig(unattended=True) "
                "(CLI: -E unattended=true) to skip operator prompts."
            ) from exc
        _drain_stdin()

    def confirm_success(self, prompt: str = "Did the robot succeed? [y/N]: ") -> bool:
        """Return whether the operator entered an affirmative verdict."""
        answer = self.input_fn(prompt)
        return answer.strip().lower() in _AFFIRMATIVE


def _drain_stdin() -> None:
    """Discard buffered TTY input so a stale newline cannot end step zero."""
    import sys

    if not sys.stdin.isatty():
        return
    if sys.platform == "win32":
        import msvcrt  # pragma: no cover - import guard

        while msvcrt.kbhit():
            msvcrt.getwch()
        return
    import select  # pragma: no cover - POSIX TTY-bound

    while select.select([sys.stdin], [], [], 0)[0]:  # pragma: no cover - POSIX TTY-bound
        sys.stdin.readline()  # pragma: no cover - POSIX TTY-bound


def default_poll_end() -> bool:
    """Return whether an operator pressed Enter without blocking."""
    import sys

    if not sys.stdin.isatty():
        return False
    if sys.platform == "win32":
        import msvcrt  # pragma: no cover - import guard

        pressed_enter = False
        while msvcrt.kbhit():
            if msvcrt.getwch() in ("\r", "\n"):
                pressed_enter = True
        return pressed_enter
    import select  # pragma: no cover - POSIX TTY-bound

    ready, _, _ = select.select([sys.stdin], [], [], 0)  # pragma: no cover - POSIX TTY-bound
    if not ready:  # pragma: no cover - POSIX TTY-bound
        return False  # pragma: no cover - POSIX TTY-bound
    sys.stdin.readline()  # pragma: no cover - POSIX TTY-bound
    return True  # pragma: no cover - POSIX TTY-bound
