"""Golden tests for India identity & bank validators."""

import pytest

from app.core.validators import (
    validate_aadhaar,
    validate_ifsc,
    validate_pan,
    validate_uan,
)

# Verhoeff-valid Aadhaar numbers (computed from the check tables).
VALID_AADHAAR = "234567890124"


class TestPAN:
    def test_normalises_and_accepts(self) -> None:
        assert validate_pan(" abcpe1234f ") == "ABCPE1234F"

    def test_rejects_wrong_shape(self) -> None:
        with pytest.raises(ValueError, match="10 characters"):
            validate_pan("ABCPE1234")  # too short

    def test_rejects_bad_holder_type(self) -> None:
        # 4th char 'Z' is not a valid holder type
        with pytest.raises(ValueError, match="holder-type"):
            validate_pan("ABCZE1234F")


class TestAadhaar:
    def test_accepts_valid_checksum(self) -> None:
        assert validate_aadhaar(VALID_AADHAAR) == VALID_AADHAAR

    def test_strips_spaces_and_dashes(self) -> None:
        spaced = f"{VALID_AADHAAR[:4]} {VALID_AADHAAR[4:8]}-{VALID_AADHAAR[8:]}"
        assert validate_aadhaar(spaced) == VALID_AADHAAR

    def test_rejects_bad_checksum(self) -> None:
        # flip the last digit -> checksum fails
        bad = VALID_AADHAAR[:-1] + ("0" if VALID_AADHAAR[-1] != "0" else "1")
        with pytest.raises(ValueError, match="checksum"):
            validate_aadhaar(bad)

    def test_rejects_wrong_length(self) -> None:
        with pytest.raises(ValueError, match="12 digits"):
            validate_aadhaar("1234")

    def test_rejects_leading_zero_or_one(self) -> None:
        with pytest.raises(ValueError, match="cannot start"):
            validate_aadhaar("123456789012")


class TestIFSC:
    def test_normalises_and_accepts(self) -> None:
        assert validate_ifsc("hdfc0001234") == "HDFC0001234"

    def test_requires_zero_in_position_five(self) -> None:
        with pytest.raises(ValueError, match="IFSC"):
            validate_ifsc("HDFCX001234")

    def test_rejects_wrong_length(self) -> None:
        with pytest.raises(ValueError, match="IFSC"):
            validate_ifsc("HDFC000123")


class TestUAN:
    def test_accepts_12_digits(self) -> None:
        assert validate_uan("1004 5678 9012") == "100456789012"

    def test_rejects_non_numeric(self) -> None:
        with pytest.raises(ValueError, match="12 digits"):
            validate_uan("10045678901X")
