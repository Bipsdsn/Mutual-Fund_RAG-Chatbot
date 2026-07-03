"""Phase 5 tests for the PII guard (Docs/evals.md E-5.1 .. E-5.12, SC5).

Pure regex logic — no Groq, no network. Verifies every PII type is detected,
values are never returned, and AUM/NAV figures are NOT false-positives.
"""

from __future__ import annotations

from backend.guardrails import pii


# ── Each PII type is detected (E-5.1..E-5.6) ──────────────────────────────
def test_pan_detected():
    assert pii.scan("my PAN is ABCDE1234F").has_pii is True
    assert "PAN" in pii.scan("ABCDE1234F").pii_types


def test_pan_lowercase_detected():
    assert pii.scan("pan abcde1234f please").has_pii is True


def test_aadhaar_detected_spaced_and_plain():
    assert pii.scan("1234 5678 9012").has_pii is True
    assert pii.scan("123456789012").has_pii is True
    assert pii.scan("1234-5678-9012").has_pii is True
    assert "AADHAAR" in pii.scan("1234 5678 9012").pii_types


def test_phone_detected():
    r = pii.scan("call me on 9876543210")
    assert r.has_pii is True and "PHONE" in r.pii_types


def test_email_detected():
    r = pii.scan("reach me at john.doe@example.com")
    assert r.has_pii is True and "EMAIL" in r.pii_types


def test_account_number_detected_in_context():
    r = pii.scan("my account number is 123456789012")
    assert r.has_pii is True and "ACCOUNT_NUMBER" in r.pii_types


def test_otp_detected_in_context():
    r = pii.scan("my otp is 482913")
    assert r.has_pii is True and "OTP" in r.pii_types


# ── No echo: result holds names only, never the value (E-5.7) ─────────────
def test_result_contains_no_values():
    r = pii.scan("my PAN ABCDE1234F and phone 9876543210")
    flat = " ".join(r.pii_types)
    assert "ABCDE1234F" not in flat
    assert "9876543210" not in flat
    assert set(r.pii_types) >= {"PAN", "PHONE"}


# ── PII + valid question → still rejected (E-5.9 / PII-8) ─────────────────
def test_pii_embedded_with_question_rejected():
    r = pii.scan("my PAN ABCDE1234F, what is the expense ratio of HDFC Mid Cap?")
    assert r.has_pii is True


# ── False-positive guards: AUM/NAV must NOT trip (E-5.10/E-5.11 / PII-7) ──
def test_aum_figure_not_flagged():
    r = pii.scan("what is the fund size of HDFC Large Cap, around 28500 crore?")
    assert r.has_pii is False


def test_nav_figure_not_flagged():
    r = pii.scan("what is the NAV 1234.56 of HDFC Mid Cap?")
    assert r.has_pii is False


def test_plain_long_number_without_account_context_not_flagged():
    # 8-18 digits but no 'account' keyword → not PII (gated).
    r = pii.scan("the scheme code is 11223344 in the factsheet")
    assert r.has_pii is False


def test_four_digit_year_without_otp_context_not_flagged():
    r = pii.scan("the fund launched in 2007")
    assert r.has_pii is False


# ── Clean factual query passes through ────────────────────────────────────
def test_clean_query_passes():
    r = pii.scan("What is the expense ratio of HDFC Mid Cap Fund?")
    assert r.has_pii is False and r.pii_types == []


def test_empty_query():
    assert pii.scan("").has_pii is False
