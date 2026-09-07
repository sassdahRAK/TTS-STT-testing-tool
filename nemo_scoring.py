"""
NeMo Scoring Module - Integrates NVIDIA NeMo's WER/CER metrics into the Model Tester Tool.

For Khmer text (no word boundaries), CER (Character Error Rate) is the correct metric.
This module wraps NeMo's word_error_rate function with use_cer=True.

Usage:
    scorer = NeMoScorer()
    result = scorer.score(reference="សូមអរគុណ", hypothesis="សុមអរគុន")
    print(result["cer"])  # 0.125 = 12.5% character error rate
"""

from dataclasses import dataclass


@dataclass
class ScoreResult:
    """Result of scoring a single transcription."""
    cer: float  # Character Error Rate (0.0 to 1.0+)
    wer: float  # Word Error Rate (0.0 to 1.0+)
    correct: int
    substitutions: int
    deletions: int
    insertions: int
    reference_length: int

    @property
    def accuracy(self) -> float:
        """1.0 - CER, clamped to 0."""
        return max(0.0, 1.0 - self.cer)

    @property
    def cer_percent(self) -> str:
        return f"{self.cer * 100:.1f}%"

    @property
    def accuracy_percent(self) -> str:
        return f"{self.accuracy * 100:.1f}%"


class NeMoScorer:
    """
    Wraps NVIDIA NeMo's word_error_rate for STT accuracy scoring.

    For Khmer and other scripts without word boundaries, always use CER.
    """

    def __init__(self):
        self._available = None

    def is_available(self) -> bool:
        """Check if NeMo ASR metrics are importable."""
        if self._available is not None:
            return self._available
        try:
            from nemo.collections.asr.metrics.wer import word_error_rate
            self._available = True
        except Exception:
            self._available = False
        return self._available

    def score(self, reference: str, hypothesis: str, use_cer: bool = True) -> ScoreResult:
        """
        Score a hypothesis (model output) against reference (ground truth).

        Args:
            reference: The correct transcript (human-verified)
            hypothesis: The model's transcription output
            use_cer: Use Character Error Rate (recommended for Khmer)

        Returns:
            ScoreResult with CER, WER, and error breakdown
        """
        if not self.is_available():
            raise ImportError(
                "NeMo ASR metrics not available. Install with: pip install nemo-toolkit[asr]"
            )

        from nemo.collections.asr.metrics.wer import word_error_rate

        if not reference:
            reference = ""
        if not hypothesis:
            hypothesis = ""

        # NeMo expects lists of strings (param names: hypotheses/references)
        cer_value = word_error_rate(
            hypotheses=[hypothesis],
            references=[reference],
            use_cer=True,
        )

        wer_value = word_error_rate(
            hypotheses=[hypothesis],
            references=[reference],
            use_cer=False,
        )

        # Calculate error breakdown
        ref_len = len(reference) if use_cer else len(reference.split())
        errors = self._calculate_errors(reference, hypothesis, use_cer)

        return ScoreResult(
            cer=float(cer_value),
            wer=float(wer_value),
            correct=errors["correct"],
            substitutions=errors["substitutions"],
            deletions=errors["deletions"],
            insertions=errors["insertions"],
            reference_length=ref_len,
        )

    def _calculate_errors(self, reference: str, hypothesis: str, use_cer: bool) -> dict:
        """
        Calculate error breakdown using Levenshtein distance.
        Returns counts of correct, substitutions, deletions, insertions.
        """
        if use_cer:
            ref_chars = list(reference)
            hyp_chars = list(hypothesis)
        else:
            ref_chars = reference.split()
            hyp_chars = hypothesis.split()

        m, n = len(ref_chars), len(hyp_chars)

        # Build DP table
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if ref_chars[i - 1] == hyp_chars[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = 1 + min(
                        dp[i - 1][j - 1],  # substitution
                        dp[i - 1][j],      # deletion
                        dp[i][j - 1],      # insertion
                    )

        # Backtrace to find error types
        i, j = m, n
        correct = 0
        substitutions = 0
        deletions = 0
        insertions = 0

        while i > 0 or j > 0:
            if i > 0 and j > 0 and ref_chars[i - 1] == hyp_chars[j - 1]:
                correct += 1
                i -= 1
                j -= 1
            elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
                substitutions += 1
                i -= 1
                j -= 1
            elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
                deletions += 1
                i -= 1
            else:
                insertions += 1
                j -= 1

        return {
            "correct": correct,
            "substitutions": substitutions,
            "deletions": deletions,
            "insertions": insertions,
        }

    def score_batch(self, references: list[str], hypotheses: list[str], use_cer: bool = True) -> dict:
        """
        Score multiple pairs at once. Returns aggregate metrics.

        Args:
            references: List of ground truth texts
            hypotheses: List of model outputs (same order)
            use_cer: Use Character Error Rate

        Returns:
            Dict with average_cer, average_wer, per_item results
        """
        if not self.is_available():
            raise ImportError("NeMo ASR metrics not available.")

        from nemo.collections.asr.metrics.wer import word_error_rate

        avg_cer = word_error_rate(hypotheses=hypotheses, references=references, use_cer=True)
        avg_wer = word_error_rate(hypotheses=hypotheses, references=references, use_cer=False)

        per_item = []
        for ref, hyp in zip(references, hypotheses):
            per_item.append(self.score(ref, hyp, use_cer))

        return {
            "average_cer": float(avg_cer),
            "average_wer": float(avg_wer),
            "per_item": per_item,
        }


# Lightweight fallback scorer when NeMo is not installed
class FallbackScorer:
    """
    Pure-Python CER/WER scorer as fallback when NeMo is not available.
    Uses the same algorithm but without NeMo dependency.
    """

    def score(self, reference: str, hypothesis: str, use_cer: bool = True) -> ScoreResult:
        if not reference:
            reference = ""
        if not hypothesis:
            hypothesis = ""

        if use_cer:
            ref_units = list(reference)
            hyp_units = list(hypothesis)
        else:
            ref_units = reference.split()
            hyp_units = hypothesis.split()

        m, n = len(ref_units), len(hyp_units)

        # DP table
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if ref_units[i - 1] == hyp_units[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = 1 + min(dp[i - 1][j - 1], dp[i - 1][j], dp[i][j - 1])

        total_errors = dp[m][n]
        ref_len = max(m, 1)

        cer = total_errors / ref_len if use_cer else 0.0
        wer = total_errors / ref_len if not use_cer else 0.0

        # Backtrace
        i, j = m, n
        correct = substitutions = deletions = insertions = 0
        while i > 0 or j > 0:
            if i > 0 and j > 0 and ref_units[i - 1] == hyp_units[j - 1]:
                correct += 1; i -= 1; j -= 1
            elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
                substitutions += 1; i -= 1; j -= 1
            elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
                deletions += 1; i -= 1
            else:
                insertions += 1; j -= 1

        return ScoreResult(
            cer=cer, wer=wer,
            correct=correct, substitutions=substitutions,
            deletions=deletions, insertions=insertions,
            reference_length=ref_len,
        )


def get_scorer():
    """
    Factory: returns NeMoScorer if available, otherwise FallbackScorer.
    Your code can just call get_scorer() without checking.
    """
    nemo = NeMoScorer()
    if nemo.is_available():
        return nemo
    return FallbackScorer()
