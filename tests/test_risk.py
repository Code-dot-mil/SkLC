from skill_exchange.risk import assess_report


def test_clean_static_report_is_low_with_low_confidence():
    assessment = assess_report(
        {
            "risk_assessment": {"score": 0, "severity": "LOW", "recommendation": "SAFE"},
            "issues": [],
            "metadata": {
                "skillspector_version": "2.1.5",
                "llm_requested": False,
                "llm_available": False,
            },
        }
    )

    assert assessment["risk"] == "Low"
    assert assessment["confidence_flags"] == ["Low confidence"]
    assert assessment["reason"] == "No medium, high, or critical findings detected."


def test_medium_report_is_medium():
    assessment = assess_report(
        {
            "risk_assessment": {"score": 45, "severity": "MEDIUM", "recommendation": "CAUTION"},
            "issues": [{"id": "EA3", "severity": "MEDIUM"}],
            "metadata": {"llm_requested": True, "llm_available": True},
        }
    )

    assert assessment["risk"] == "Medium"
    assert assessment["confidence_flags"] == []


def test_high_report_is_high():
    assessment = assess_report(
        {
            "risk_assessment": {"score": 85, "severity": "HIGH", "recommendation": "BLOCK"},
            "issues": [{"id": "E2", "severity": "HIGH"}],
            "metadata": {"llm_requested": True, "llm_available": True},
        }
    )

    assert assessment["risk"] == "High"
    assert assessment["confidence_flags"] == []


def test_malformed_report_is_unknown():
    assessment = assess_report({"unexpected": "shape"})

    assert assessment["risk"] == "Unknown"
    assert assessment["reason"] == "Scanner report did not match the expected SkillSpector shape."


def test_failed_execution_is_unknown_even_when_report_contains_risks():
    assessment = assess_report(
        {
            "execution_successful": False,
            "risk_assessment": {"score": 100, "severity": "CRITICAL", "recommendation": "BLOCK"},
            "issues": [{"id": "E2", "severity": "HIGH"}],
            "metadata": {"llm_requested": True},
        }
    )

    assert assessment["risk"] == "Unknown"
    assert assessment["reason"] == "scanner_failed: SkillSpector reported execution_successful=false"
