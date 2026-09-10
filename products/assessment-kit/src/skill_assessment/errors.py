from __future__ import annotations


class AssessmentError(Exception):
    """A user-facing assessment-kit failure."""

    exit_code = 2


class RetryableAssessmentError(AssessmentError):
    """An assessor failure that a caller may retry."""

    exit_code = 10
