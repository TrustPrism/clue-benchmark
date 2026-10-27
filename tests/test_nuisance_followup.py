import pytest

from clue_benchmark.nuisance_followup import (
    CAP,
    PROBES,
    prepare_followup,
    select_cohort,
)


def test_single_allowance_selects_balanced_prefix():
    blocks = [
        {"maximum_microdollars": 1_000_000, "context_fits": True, "burden": n % 2}
        for n in range(12)
    ]
    selected = select_cohort(blocks)
    assert len(selected) == 8
    assert sum(b["maximum_microdollars"] for b in selected) + PROBES <= CAP
    assert [b["burden"] for b in selected].count(0) == 4
    blocks[0]["context_fits"] = False
    assert select_cohort(blocks) == []


def test_unaffordable_does_not_increase_allowance():
    assert (
        select_cohort([{"maximum_microdollars": 2_000_000, "context_fits": True}] * 12)
        == []
    )


def test_no_implicit_model_substitution(tmp_path):
    with pytest.raises(ValueError, match="exact motivating"):
        prepare_followup(tmp_path / "study", [])
    assert not (tmp_path / "study").exists()


def test_paired_analysis_averages_worlds_and_has_small_exact_resolution():
    from clue_benchmark.followup_analysis import paired_contrast

    result = paired_contrast({"a": 0, "b": 0.5, "c": 1}, {"a": 1, "b": 0.5, "c": 0})
    assert result["mean_change"] == 0
    assert result["gained_worlds"] == result["lost_worlds"] == 1
    assert result["exact_two_sided_p"] == 1
    assert result["randomization_resolution"] == 1 / 8
    with pytest.raises(ValueError, match="same nonempty"):
        paired_contrast({"a": 1}, {"b": 0})
