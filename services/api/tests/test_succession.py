"""Golden tests for succession bench-strength."""

from app.contexts.succession.service import bench_strength


def test_empty_bench_is_at_risk() -> None:
    b = bench_strength([])
    assert b.status == "at_risk"
    assert b.ready_now == 0 and b.total == 0 and b.pipeline == 0


def test_pipeline_only_is_developing() -> None:
    b = bench_strength(["1_2_years", "3_5_years"])
    assert b.status == "developing"
    assert b.ready_now == 0 and b.pipeline == 2 and b.total == 2


def test_one_ready_now_is_covered() -> None:
    b = bench_strength(["ready_now", "3_5_years"])
    assert b.status == "covered"
    assert b.ready_now == 1 and b.pipeline == 1 and b.total == 2
