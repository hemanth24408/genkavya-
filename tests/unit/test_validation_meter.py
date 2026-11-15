from types import SimpleNamespace

import pytest

from genkavya.contracts.common import CheckStatus
from genkavya.validation.meter import validate_meter


def fake_chanda(monkeypatch, lengths, patterns, error=None, empty_marker_at=None):
    def analyze_text(*args, **kwargs):
        if error:
            raise error
        lines = []
        for i, (length, pattern) in enumerate(zip(lengths, patterns)):
            marks = [{"L": "ल", "G": "ग", "X": "ग"}.get(mark, mark) for mark in pattern]
            if empty_marker_at is not None and i == 0:
                marks.insert(empty_marker_at, "")
            lines.append(SimpleNamespace(result=SimpleNamespace(length=length, lg=marks)))
        return SimpleNamespace(result=SimpleNamespace(line=lines))
    monkeypatch.setitem(__import__("sys").modules, "chanda", SimpleNamespace(analyze_text=analyze_text))


PADA = ("x x x x x x x x",) * 4


def test_meter_passes_only_the_three_project_rules(monkeypatch):
    fake_chanda(monkeypatch, [8] * 4, ["XXXXLGGX", "XXXXLGLX", "XXXXLGGX", "XXXXLGLX"])
    result = validate_meter(PADA)
    assert result.status == CheckStatus.PASSED
    assert [check.status for check in result.checks] == [CheckStatus.PASSED] * 3


def test_meter_fails_on_wrong_count_or_cadence(monkeypatch):
    fake_chanda(monkeypatch, [8, 8, 8, 8], ["XXXXLGGX", "XXXXLLLL", "XXXXLLLL", "XXXXLGLX"])
    result = validate_meter(PADA)
    assert result.status == CheckStatus.FAILED
    assert result.checks[1].status == CheckStatus.PASSED
    assert result.checks[2].status == CheckStatus.FAILED

    fake_chanda(monkeypatch, [8, 7, 8, 8], ["XXXXLGGX", "XXXXLGL", "XXXXLGGX", "XXXXLGLX"])
    count_result = validate_meter(PADA)
    assert count_result.status == CheckStatus.FAILED
    assert count_result.checks[1].status == CheckStatus.FAILED


def test_chanda_error_is_unverified_not_failed(monkeypatch):
    fake_chanda(monkeypatch, [], [], RuntimeError("backend unavailable"))
    result = validate_meter(PADA)
    assert result.status == CheckStatus.UNVERIFIED
    assert all(check.status != CheckStatus.FAILED for check in result.checks)


def test_incomplete_analysis_is_unverified(monkeypatch):
    fake_chanda(monkeypatch, [8] * 3, ["XXXXLGGX"] * 3)
    assert validate_meter(PADA).status == CheckStatus.UNVERIFIED


@pytest.mark.parametrize("line_break", ["\n", "\r"])
def test_embedded_line_break_fails_structure_without_calling_chanda(monkeypatch, line_break):
    import sys
    from types import SimpleNamespace

    calls = []

    def analyze_text(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("Chanda must not receive multiline padas")

    monkeypatch.setitem(sys.modules, "chanda", SimpleNamespace(analyze_text=analyze_text))
    padas = (PADA[0], f"first{line_break}second", PADA[2], PADA[3])

    result = validate_meter(padas)

    assert result.checks[0].status == CheckStatus.FAILED
    assert result.checks[1].status == CheckStatus.UNVERIFIED
    assert result.checks[2].status == CheckStatus.UNVERIFIED
    assert "position(s): 2" in result.checks[0].explanation
    assert result.syllable_counts == [None] * 4
    assert calls == []


def test_multiple_multiline_padas_are_all_identified_before_chanda(monkeypatch):
    import sys
    from types import SimpleNamespace

    calls = []
    monkeypatch.setitem(
        sys.modules,
        "chanda",
        SimpleNamespace(analyze_text=lambda *args, **kwargs: calls.append((args, kwargs))),
    )
    padas = (f"{PADA[0]}\nextra", PADA[1], f"{PADA[2]}\rcontinued", PADA[3])

    result = validate_meter(padas)

    assert result.checks[0].status == CheckStatus.FAILED
    assert "position(s): 1, 3" in result.checks[0].explanation
    assert result.checks[1].status == CheckStatus.UNVERIFIED
    assert result.checks[2].status == CheckStatus.UNVERIFIED
    assert calls == []


def test_interior_empty_chanda_marker_is_ignored_and_laghu_guru_order_is_preserved(monkeypatch):
    expected = ["XXXXLGGX", "XXXXLGLX", "XXXXLGGX", "XXXXLGLX"]
    fake_chanda(monkeypatch, [8] * 4, expected, empty_marker_at=5)
    result = validate_meter(PADA)
    assert result.status == CheckStatus.PASSED
    assert result.syllable_counts == [8] * 4
    assert result.laghu_guru_patterns == ["GGGGLGGG", "GGGGLGLG", "GGGGLGGG", "GGGGLGLG"]


def test_unknown_nonempty_marker_is_unverified(monkeypatch):
    import sys
    from types import SimpleNamespace

    def analyze_text(*args, **kwargs):
        line = SimpleNamespace(result=SimpleNamespace(length=8, lg=["ल", "ग", "?", "ल", "ग", "ल", "ग", "ल"]))
        return SimpleNamespace(result=SimpleNamespace(line=[line] * 4))

    monkeypatch.setitem(sys.modules, "chanda", SimpleNamespace(analyze_text=analyze_text))
    result = validate_meter(PADA)
    assert result.status == CheckStatus.UNVERIFIED
    assert result.checks[1].status == CheckStatus.UNVERIFIED
    assert result.checks[2].status == CheckStatus.UNVERIFIED


def test_marker_count_mismatch_is_unverified(monkeypatch):
    import sys
    from types import SimpleNamespace

    def analyze_text(*args, **kwargs):
        line = SimpleNamespace(result=SimpleNamespace(length=8, lg=["ल", "ग", "ल", "ग", "ल", "ग", "ल"]))
        return SimpleNamespace(result=SimpleNamespace(line=[line] * 4))

    monkeypatch.setitem(sys.modules, "chanda", SimpleNamespace(analyze_text=analyze_text))
    result = validate_meter(PADA)
    assert result.status == CheckStatus.UNVERIFIED
    assert all(check.status == CheckStatus.UNVERIFIED for check in result.checks[1:])


def test_thirteen_to_fifteen_syllables_fail_the_eight_syllable_rule(monkeypatch):
    fake_chanda(
        monkeypatch,
        [13, 14, 15, 14],
        ["L" * 13, "G" * 14, "L" * 15, "G" * 14],
    )
    result = validate_meter(PADA)
    assert result.status == CheckStatus.FAILED
    assert result.syllable_counts == [13, 14, 15, 14]
    assert result.checks[1].status == CheckStatus.FAILED
    assert result.checks[2].status == CheckStatus.UNVERIFIED
    assert "13, 14, 15, 14" in result.checks[1].explanation


def test_real_chanda_devanagari_smoke_test():
    pytest.importorskip("chanda")
    padas = (
        "वागर्थाविव संपृक्तौ", "वागर्थप्रतिपत्तये",
        "जगतः पितरौ वंदे", "पार्वतीपरमेश्वरौ",
    )
    result = validate_meter(padas)
    assert result.pada_count == 4
    assert result.syllable_counts == [8, 8, 8, 8]
    assert result.laghu_guru_patterns == ["GGGLLGGG", "GGGLLGLG", "LLGLLGGG", "GLGLLGLG"]
    assert result.status == CheckStatus.PASSED
