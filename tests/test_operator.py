from __future__ import annotations

import pytest
from inspect_robots.errors import EmbodimentFault

from inspect_robots_franka.operator import OperatorIO, _drain_stdin, default_poll_end


def _scripted(answers: list[str]):
    seen: list[str] = []

    def input_fn(prompt: str) -> str:
        seen.append(prompt)
        return answers.pop(0)

    return input_fn, seen


def test_wait_ready_reads_prompt() -> None:
    input_fn, seen = _scripted([""])
    OperatorIO(input_fn=input_fn, output_fn=lambda _line: None).wait_ready("ready?")
    assert seen == ["ready?"]


@pytest.mark.parametrize("exception", [EOFError, OSError])
def test_wait_ready_turns_dead_stdin_into_embodiment_fault(
    exception: type[Exception],
) -> None:
    def input_fn(_prompt: str) -> str:
        raise exception("closed")

    with pytest.raises(EmbodimentFault, match=r"FrankaConfig\(unattended=True\)"):
        OperatorIO(input_fn=input_fn).wait_ready()


@pytest.mark.parametrize("answer", ["y", "Yes", "1", "TRUE", "success", "pass"])
def test_confirm_success_affirmative(answer: str) -> None:
    assert OperatorIO(input_fn=lambda _prompt: answer).confirm_success() is True


@pytest.mark.parametrize("answer", ["n", "no", "", "nope"])
def test_confirm_success_negative(answer: str) -> None:
    assert OperatorIO(input_fn=lambda _prompt: answer).confirm_success() is False


def test_default_poll_is_exposed() -> None:
    assert callable(default_poll_end)


def test_drain_stdin_non_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    _drain_stdin()


def test_default_poll_end_non_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)
    assert default_poll_end() is False


class DummyMsvcrt:
    def __init__(self, chars: list[str]) -> None:
        self.chars = chars

    def kbhit(self) -> bool:
        return bool(self.chars)

    def getwch(self) -> str:
        return self.chars.pop(0)


def test_drain_stdin_win32(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    dummy = DummyMsvcrt(["a", "\n"])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "msvcrt", dummy)
    _drain_stdin()
    assert dummy.chars == []


def test_default_poll_end_win32_enter(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    dummy = DummyMsvcrt(["a", "\r"])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "msvcrt", dummy)
    assert default_poll_end() is True
    assert dummy.chars == []


def test_default_poll_end_win32_no_enter(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    dummy = DummyMsvcrt(["a", "b"])
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "msvcrt", dummy)
    assert default_poll_end() is False
    assert dummy.chars == []
