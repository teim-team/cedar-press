"""Fixture-only tests of the subaward money fence in 41_match_subawards_to_ledger.py.

The fence is the one place the subaward-versus-prime rule is written; 45 and 94
reach it through `m41`, and Lumecon-data's release projection applies the same
rule, so the cases below use the producer's own fixture amounts and expected
strings (tests/test_press_candidates.py, money_fence_fixture) to prove the two
sides agree cell for cell. No file is read or written.
"""
import importlib.util
import unittest
from pathlib import Path

CODE = Path(__file__).resolve().parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), CODE / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m41 = load("41_match_subawards_to_ledger.py")
m45 = load("45_promote_subawards.py")


class SubawardMoneyFenceTests(unittest.TestCase):
    def test_both_amounts_reported_gives_yes_or_no_and_a_four_place_ratio(self):
        # Before 2026-10-02 the not-exceeding case returned "" rather than "no".
        self.assertEqual(m41.subaward_money_fence("32386.40", "435776165.40"),
                         ("no", "0.0001", ""))
        self.assertEqual(m41.subaward_money_fence("1518000.00", "8982813.84")[:2],
                         ("no", "0.1690"))
        self.assertEqual(m41.subaward_money_fence("1282234055.8", "13406053.11")[:2],
                         ("yes", "95.6459"))

    def test_zero_prime_under_positive_subaward_is_yes_with_undefined_ratio_and_a_reason(self):
        # The served row 000375DB-0EC4-4293-B372-61CB6E8F9B8D: both blank before.
        flag, ratio, note = m41.subaward_money_fence("3299182.00", "0.00")
        self.assertEqual((flag, ratio), ("yes", ""))
        self.assertIn("reported as 0.00", note)
        self.assertIn("ratio is undefined", note)
        self.assertIn("positive subaward exceeds a non-positive reported prime", note)
        flag, ratio, note = m41.subaward_money_fence("0", "0.00")
        self.assertEqual((flag, ratio), ("no", ""))
        self.assertIn("does not exceed", note)
        self.assertEqual(m41.subaward_money_fence("5.00", "-1.00")[:2], ("yes", ""))

    def test_unreported_amount_leaves_both_blank_and_names_the_missing_amount(self):
        for sub, prime, missing in (("100.00", "", "prime_award_amount"),
                                    ("", "100.00", "subaward_amount"),
                                    (None, None, "subaward_amount and prime_award_amount"),
                                    ("100.00", "n/a", "prime_award_amount")):
            with self.subTest(sub=sub, prime=prime):
                flag, ratio, note = m41.subaward_money_fence(sub, prime)
                self.assertEqual((flag, ratio), ("", ""))
                self.assertIn(missing + " not reported", note)

    def test_ratio_quantizes_half_even_like_the_release_projection(self):
        # 1/32 = 0.03125 is an exact tie at the fifth place; the producer's
        # Decimal quantize(ROUND_HALF_EVEN) gives 0.0312, and so must this.
        self.assertEqual(m41.subaward_money_fence("1", "32")[1], "0.0312")
        self.assertEqual(m41.subaward_money_fence("3", "32")[1], "0.0938")

    def test_legacy_float_callers_get_the_same_answer_as_string_callers(self):
        self.assertEqual(m41.subaward_money_fence(32386.40, 435776165.40),
                         m41.subaward_money_fence("32386.40", "435776165.40"))
        self.assertEqual(m41.subaward_money_fence(0.1, 0.3)[1], "0.3333")
        self.assertIsNone(m41.reported_amount(float("nan")))
        self.assertIsNone(m41.reported_amount(True))

    def test_45_qc_delegates_to_the_fence_and_keeps_its_ratio_flag_order(self):
        self.assertEqual(m45.qc("1", "4"), ("0.2500", "no"))
        self.assertEqual(m45.qc("100.00", "0"), ("", "yes"))
        self.assertEqual(m45.qc("100.00", ""), ("", ""))

    def test_staged_rows_carry_the_reason_column(self):
        self.assertIn("research_note", m41.OUT_COLS)
        self.assertEqual(m41.OUT_COLS.index("subaward_to_prime_ratio") + 1,
                         m41.OUT_COLS.index("subaward_exceeds_prime_flag"))


if __name__ == "__main__":
    unittest.main()
