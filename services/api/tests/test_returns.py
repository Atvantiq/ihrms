"""Golden tests for statutory return-file generators (PF ECR, ESI, PT)."""


from app.contexts.payroll.returns import (
    ECR_SEP,
    Member,
    ecr_file,
    ecr_line,
    esi_file,
    pt_file,
)
from app.core.money import D


def _m(**kw: object) -> Member:
    base: dict[str, object] = dict(
        employee_code="ATV-1", name="Asha Rao", uan="100200300400",
        esic_ip="3100000001", pt_state="KA", gross=D(50000), basic=D(40000),
        working_days=30, lop_days=D(0),
    )
    base.update(kw)
    return Member(**base)  # type: ignore[arg-type]


class TestEcr:
    def test_line_has_11_fields(self) -> None:
        parts = ecr_line(_m()).split(ECR_SEP)
        assert len(parts) == 11

    def test_pf_wage_capped_and_splits(self) -> None:
        # basic 40000 -> PF wage capped at 15000; EE 1800, EPS 1250, ER-EPF 550
        p = ecr_line(_m(basic=D(40000))).split(ECR_SEP)
        assert p[0] == "100200300400"      # UAN
        assert p[3] == "15000"             # EPF wages (capped)
        assert p[6] == "1800"              # EPF employee contribution
        assert p[7] == "1250"              # EPS contribution
        assert p[8] == "550"               # EPF employer share (1800-1250)
        assert p[9] == "0"                 # NCP days

    def test_ncp_days_from_lop(self) -> None:
        p = ecr_line(_m(lop_days=D(3))).split(ECR_SEP)
        assert p[9] == "3"

    def test_file_skips_zero_basic(self) -> None:
        text = ecr_file([_m(), _m(basic=D(0))])
        assert text.count("\n") == 1  # only the one contributing member


class TestEsi:
    def test_applies_within_ceiling(self) -> None:
        # gross 20000 <= 21000 -> ESI applies; 0.75% = 150
        out = esi_file([_m(gross=D(20000), basic=D(20000))])
        assert "3100000001,Asha Rao,30,20000,150,0" in out

    def test_excludes_above_ceiling(self) -> None:
        out = esi_file([_m(gross=D(50000))])
        # only the header row
        assert out.strip().count("\n") == 0

    def test_zero_paid_days_reason_code(self) -> None:
        out = esi_file([_m(gross=D(20000), basic=D(20000), lop_days=D(30))])
        # IP, name, 0 days, gross 20000, contribution 150, reason 2
        assert out.strip().endswith(",0,20000,150,2")


class TestPt:
    def test_charged_above_threshold(self) -> None:
        out = pt_file([_m(gross=D(50000))])
        assert "KA,ATV-1,Asha Rao,50000,200" in out

    def test_exempt_low_earner_excluded(self) -> None:
        out = pt_file([_m(gross=D(5000))])
        assert out.strip().count("\n") == 0  # header only
