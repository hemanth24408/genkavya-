# GenKavya validation

The Validation Module runs three independent checks: exact mandatory-word usage, project-specific meter rules, and conservative grammar assessment.

## Per-candidate evaluation

The generation response contains exactly five structurally parsed candidates. Evaluation returns one result for each candidate; a missing mandatory word or failed/unverified meter check never removes a poem from the response. The report has no overall valid/invalid candidate groups. It keeps mandatory-word, meter, and grammar results independent, and flags repeated poem text as a duplicate while retaining its evaluation.

Mandatory-word evaluation uses the original four input positions and verified approved forms. A matched form must be an exact standalone token, and one occurrence can satisfy only one position. The CLI reports `ALL WORDS PRESENT`, `SOME WORDS MISSING`, or `WORD CHECK UNVERIFIED`, with matched forms and missing or unresolved positions.

Meter evaluation reports its status, four syllable counts, Laghu/Guru patterns when available, and the validator's check explanations. `unverified` means the analysis could not establish the result; it is not reported as a confirmed meter failure. Grammar is reported independently as `verified`, `issues_found`, or `unverified`. The CLI displays the grammar status only.

## Meter scope

Chanda provides per-pāda syllable counts and Laghu/Guru analysis. GenKavya applies exactly these checks:

1. Four non-empty pādas.
2. Eight syllables in every pāda.
3. Pādas 1 and 3 have Laghu–Guru–Guru at positions 5–7; pādas 2 and 4 have Laghu–Guru–Laghu at those positions.

The module does not require Chanda to classify the complete verse as Anuṣṭubh and does not check other traditional rules. Chanda errors, unavailable results, or incomplete syllable/weight data produce `unverified`, never a confirmed metrical failure.

## Chanda dependency

Chanda is an optional dependency under the `validation` extra. Install it with:

```powershell
python -m pip install -e ".[validation]"
```

The selected constraint is `chanda>=1.1,<1.2`, matching the API version tested here. Chanda is licensed under AGPL-3.0-or-later. Optional installation does not exempt users who distribute it or a combined application from applicable license obligations. Review the license before distribution, especially for a proprietary combined application or a modified service offered over a network.

## Grammar limitation

The existing Sanskrit analyzer provides word-level diagnostics, not dependable sentence-level grammar verification. The current modular grammar validator therefore reports `unverified`; it does not ask the generation model to validate itself and does not infer incorrect grammar from parser absence.

## Test evidence

Mocked tests verify status mapping and software behavior. The Chanda smoke test uses Apte Appendix I's cited Sanskrit verse as an API fixture. It verifies the observed library output and project checks, but does not replace independent Sanskrit expert review of meter edge cases or generated poetry.
