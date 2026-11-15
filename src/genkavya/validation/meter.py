"""Project-specific Pathyā checks using Chanda only for per-pāda analysis."""

from __future__ import annotations

from collections.abc import Sequence

from genkavya.contracts.common import CheckStatus
from genkavya.contracts.generation import MeterName, SanskritCandidate
from genkavya.contracts.validation import MeterCheckName, MeterRuleResult, MeterValidation


_LAGHU = "ल"
_GURU = "ग"
_EXPECTED = ("LGG", "LGL", "LGG", "LGL")
_CHECKS = (
    MeterCheckName.PADA_STRUCTURE,
    MeterCheckName.SYLLABLE_COUNT,
    MeterCheckName.LAGHU_GURU_PATTERN,
)


def _status(checks: Sequence[MeterRuleResult]) -> CheckStatus:
    statuses = {check.status for check in checks}
    if CheckStatus.FAILED in statuses:
        return CheckStatus.FAILED
    if CheckStatus.UNVERIFIED in statuses:
        return CheckStatus.UNVERIFIED
    return CheckStatus.PASSED


def _make_result(
    pada_count: int, counts: list[int | None], patterns: list[str | None],
    checks: list[MeterRuleResult], explanation: str
) -> MeterValidation:
    return MeterValidation(
        status=_status(checks),
        meter=MeterName.CLASSICAL_ANUSTUBH,
        pada_count=pada_count,
        syllable_counts=counts if len(counts) == 4 else [None, None, None, None],
        laghu_guru_patterns=patterns if len(patterns) == 4 else [None, None, None, None],
        checks=tuple(checks),
        explanation=explanation,
        method="chanda.analyze_text per-pada analysis; GenKavya project checks",
    )


def validate_meter(candidate: SanskritCandidate | Sequence[str]) -> MeterValidation:
    """Check four-pāda structure, eight syllables each, and positions 5–7 only."""
    padas = candidate.padas if isinstance(candidate, SanskritCandidate) else tuple(candidate)
    if len(padas) != 4 or any(not isinstance(pada, str) or not pada.strip() for pada in padas):
        checks = [
            MeterRuleResult(check=MeterCheckName.PADA_STRUCTURE, status=CheckStatus.FAILED,
                            explanation="Exactly four non-empty pādas are required."),
            MeterRuleResult(check=MeterCheckName.SYLLABLE_COUNT, status=CheckStatus.UNVERIFIED,
                            explanation="Syllable analysis was skipped because pāda structure is invalid."),
            MeterRuleResult(check=MeterCheckName.LAGHU_GURU_PATTERN, status=CheckStatus.UNVERIFIED,
                            explanation="Laghu/Guru analysis was skipped because pāda structure is invalid."),
        ]
        return _make_result(len(padas), [], [], checks, "Pāda structure failed; remaining checks are unverified.")

    multiline_positions = [
        position for position, pada in enumerate(padas, start=1)
        if "\n" in pada or "\r" in pada
    ]
    if multiline_positions:
        positions = ", ".join(str(position) for position in multiline_positions)
        explanation = (
            "Embedded newline or carriage return in pada position(s): "
            f"{positions}. Each pada must be one single-line string."
        )
        checks = [
            MeterRuleResult(
                check=MeterCheckName.PADA_STRUCTURE,
                status=CheckStatus.FAILED,
                explanation=explanation,
            ),
            MeterRuleResult(
                check=MeterCheckName.SYLLABLE_COUNT,
                status=CheckStatus.UNVERIFIED,
                explanation="Syllable analysis was skipped because pada structure is invalid.",
            ),
            MeterRuleResult(
                check=MeterCheckName.LAGHU_GURU_PATTERN,
                status=CheckStatus.UNVERIFIED,
                explanation="Laghu/Guru analysis was skipped because pada structure is invalid.",
            ),
        ]
        return _make_result(
            4, [], [], checks,
            f"Pāda structure failed: {explanation} Syllable and cadence checks are unverified.",
        )

    structure = MeterRuleResult(
        check=MeterCheckName.PADA_STRUCTURE, status=CheckStatus.PASSED,
        explanation="Exactly four non-empty pādas were supplied.",
    )
    try:
        from chanda import analyze_text

        analysis = analyze_text("\n".join(padas), verse_mode=True, fuzzy=False)
        line_results = analysis.result.line
        if len(line_results) != 4:
            raise ValueError(f"Chanda returned {len(line_results)} pāda analyses; expected four.")
        counts: list[int | None] = []
        patterns: list[str | None] = []
        for line in line_results:
            result = line.result
            count = result.length
            marks = result.lg
            if not isinstance(count, int) or not isinstance(marks, (list, tuple)):
                raise ValueError("Chanda returned an incomplete syllable analysis.")
            recognized = ["L" if mark == _LAGHU else "G" for mark in marks if mark in (_LAGHU, _GURU)]
            unknown_marks = [mark for mark in marks if mark not in (_LAGHU, _GURU, "")]
            if unknown_marks:
                raise ValueError("Chanda returned unrecognized Laghu/Guru markers.")
            if len(recognized) != count:
                raise ValueError(
                    "Chanda's recognized Laghu/Guru marker count does not match its reported syllable count."
                )
            counts.append(count)
            patterns.append("".join(recognized))
    except Exception as exc:
        checks = [
            structure,
            MeterRuleResult(check=MeterCheckName.SYLLABLE_COUNT, status=CheckStatus.UNVERIFIED,
                            explanation=f"Chanda could not establish syllable counts: {exc}"),
            MeterRuleResult(check=MeterCheckName.LAGHU_GURU_PATTERN, status=CheckStatus.UNVERIFIED,
                            explanation="Chanda could not establish a complete Laghu/Guru pattern."),
        ]
        return _make_result(4, [], [], checks, "Meter analysis is unverified because Chanda did not return complete results.")

    count_status = CheckStatus.FAILED if any(count != 8 for count in counts) else CheckStatus.PASSED
    count_explanation = (
        f"Pāda syllable counts are {counts}; each must contain exactly eight syllables."
        if count_status == CheckStatus.FAILED else "All four pādas contain exactly eight syllables."
    )
    count_check = MeterRuleResult(
        check=MeterCheckName.SYLLABLE_COUNT, status=count_status, explanation=count_explanation
    )

    if any(pattern is None for pattern in patterns):
        pattern_status = CheckStatus.UNVERIFIED
        pattern_explanation = "Chanda did not provide a complete Laghu/Guru sequence for every pāda."
    elif count_status == CheckStatus.FAILED:
        pattern_status = CheckStatus.UNVERIFIED
        pattern_explanation = "The cadence check requires eight syllables per pāda and was not assessed."
    else:
        failures = [
            f"pāda {index + 1} has positions 5–7 {pattern[4:7]}, expected {_EXPECTED[index]}"
            for index, pattern in enumerate(patterns)
            if pattern[4:7] != _EXPECTED[index]
        ]
        pattern_status = CheckStatus.FAILED if failures else CheckStatus.PASSED
        pattern_explanation = "; ".join(failures) if failures else (
            "Pādas 1 and 3 match L–G–G and pādas 2 and 4 match L–G–L at positions 5–7."
        )
    pattern_check = MeterRuleResult(
        check=MeterCheckName.LAGHU_GURU_PATTERN,
        status=pattern_status,
        explanation=pattern_explanation,
    )
    checks = [structure, count_check, pattern_check]
    status = _status(checks)
    return _make_result(4, counts, patterns, checks, "All required project-specific meter checks passed." if status == CheckStatus.PASSED else "One or more required meter checks did not pass.")
