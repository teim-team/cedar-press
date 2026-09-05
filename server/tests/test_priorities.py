"""Shape the Research: the points rule, proven on an in-memory store.

Each test states a rule from ``priorities.py``'s header and plants the case
that would break it: forty sign-ins in a month, an organization with fifty
seats, points spent on two priorities at once, a subscriber who vanishes
for two years, a request that reads as an existing priority.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cedar_press import priorities as pr  # noqa: E402

_REPO = Path(__file__).resolve().parents[2]
PRESS = pr.Account(account_id="acct-tribe", user_id="clerk@tribe.example", tier="press")
PRO = pr.Account(account_id="acct-bank", user_id="analyst@bank.example", tier="press_pro")
SEAT_2 = pr.Account(account_id="acct-bank", user_id="second@bank.example", tier="press_pro")


def store() -> pr.Priorities:
    s = pr.Priorities(":memory:")
    s.seed()
    return s


class TestEarning(unittest.TestCase):
    def test_a_month_credits_once_however_many_sign_ins(self) -> None:
        s = store()
        self.assertEqual(s.accrue(PRESS, "2026-09"), 1)
        for _ in range(40):
            self.assertEqual(s.accrue(PRESS, "2026-09"), 0)
        self.assertEqual(s.balance(PRESS.account_id), 1)
        # The next month credits again; a skipped month never does.
        self.assertEqual(s.accrue(PRESS, "2026-11"), 1)
        self.assertEqual(s.balance(PRESS.account_id), 2)

    def test_press_earns_one_and_plus_earns_two(self) -> None:
        s = store()
        self.assertEqual(s.accrue(PRESS, "2026-09"), 1)
        self.assertEqual(s.accrue(PRO, "2026-09"), 2)
        self.assertEqual(s.accrue(pr.Account("acct-x", "x", "grove"), "2026-09"), 0)

    def test_an_organization_earns_per_subscription_not_per_seat(self) -> None:
        s = store()
        self.assertEqual(s.accrue(PRO, "2026-09"), 2)
        self.assertEqual(s.accrue(SEAT_2, "2026-09"), 0)
        self.assertEqual(s.balance("acct-bank"), 2)

    def test_points_expire_twelve_months_on_oldest_first(self) -> None:
        s = store()
        s.accrue(PRO, "2024-06")  # 2
        s.accrue(PRO, "2024-07")  # 2
        s.allocate(PRO, "ds-enterprise-ownership", 3)  # spends the June 2 and one of July
        self.assertEqual(s.balance("acct-bank"), 1)
        # Twelve months after July, the unspent July point expires; nothing else can.
        s.accrue(PRO, "2025-07")  # +2, and the 2024-07 leftover (1) is written off
        self.assertEqual(s.balance("acct-bank"), 2)
        activity = s.influence(PRO, "2025-07")["activity"]
        expirations = [a for a in activity if a["reason"] == "expiration"]
        self.assertEqual([a["amount"] for a in expirations], [-1])
        # Idempotent: another accrual in the same month writes nothing more off.
        s.accrue(PRO, "2025-07")
        self.assertEqual(s.balance("acct-bank"), 2)
        # A subscriber who vanishes for two years returns with nothing banked.
        s.accrue(PRESS, "2024-01")
        s.accrue(PRESS, "2026-09")
        self.assertEqual(s.balance("acct-tribe"), 1)


class TestSpending(unittest.TestCase):
    def test_points_go_where_the_subscriber_puts_them_and_come_back(self) -> None:
        s = store()
        s.accrue(PRO, "2026-08")
        s.accrue(PRO, "2026-09")
        self.assertEqual(s.balance("acct-bank"), 4)
        s.allocate(PRO, "ds-enterprise-ownership", 3)
        s.allocate(PRO, "rq-energy-financing", 1)
        self.assertEqual(s.balance("acct-bank"), 0)
        with self.assertRaises(pr.PointsError):
            s.allocate(PRO, "ds-tribal-state-compacts", 1)
        with self.assertRaises(pr.PointsError):
            s.allocate(PRO, "rq-energy-financing", -2)
        with self.assertRaises(pr.PointsError):
            s.allocate(PRO, "no-such-priority", 1)
        with self.assertRaises(pr.PointsError):
            s.allocate(PRO, "rq-energy-financing", 0)
        back = s.allocate(PRO, "ds-enterprise-ownership", -1)
        self.assertEqual(back["points_available"], 1)
        self.assertEqual(back["your_points"], 2)
        top = s.priorities()[0]
        self.assertEqual(
            (top["id"], top["points"], top["subscribers"]), ("ds-enterprise-ownership", 2, 1)
        )

    def test_a_priority_shows_points_and_how_many_subscriptions_put_them_there(self) -> None:
        s = store()
        s.accrue(PRO, "2026-09")
        s.accrue(PRESS, "2026-09")
        s.allocate(PRO, "ds-enterprise-ownership", 2)
        s.allocate(PRESS, "ds-enterprise-ownership", 1)
        p = s.priority("ds-enterprise-ownership")
        self.assertEqual((p["points"], p["subscribers"]), (3, 2))
        # Two seats of one organization count once.
        s.accrue(SEAT_2, "2026-10")
        s.allocate(SEAT_2, "ds-enterprise-ownership", 1)
        p = s.priority("ds-enterprise-ownership")
        self.assertEqual((p["points"], p["subscribers"]), (4, 2))

    def test_the_ledger_explains_every_point(self) -> None:
        s = store()
        s.accrue(PRO, "2026-08")
        s.allocate(PRO, "ds-historical-lobbying", 1)
        s.allocate(PRO, "ds-historical-lobbying", -1)
        reasons = [a["reason"] for a in s.influence(PRO, "2026-09")["activity"]]
        self.assertEqual(reasons, ["refund", "allocation", "monthly_activity"])
        self.assertTrue(set(reasons) <= set(pr.REASONS))


class TestInfluence(unittest.TestCase):
    def test_the_profile_card_reads_from_the_ledger(self) -> None:
        s = store()
        card = s.influence(PRO, "2026-09")
        self.assertEqual(card["points_available"], 0)
        self.assertFalse(card["credited_this_month"])
        self.assertEqual(card["next_credit"], {"points": 2, "month": "2026-09"})
        s.accrue(PRO, "2026-09")
        s.allocate(PRO, "ds-enterprise-ownership", 1)
        s.submit_request(
            PRO,
            "Which tribal enterprises own which subsidiaries, for vendor diligence",
            "vendor diligence",
            "ds-enterprise-ownership",
        )
        card = s.influence(PRO, "2026-09")
        self.assertTrue(card["credited_this_month"])
        self.assertEqual(card["next_credit"], {"points": 2, "month": "2026-10"})
        self.assertEqual(card["points_available"], 1)
        self.assertEqual(card["allocations"][0]["points"], 1)
        self.assertEqual(card["requests"][0]["status"], "associated")
        self.assertEqual(card["expiry_months"], 12)


class TestRequests(unittest.TestCase):
    def test_a_request_reads_as_the_priority_it_is_about(self) -> None:
        s = store()
        text = "I wish you had a dataset showing which tribal enterprises own which subsidiaries"
        hits = pr.related(text, s.priorities())
        self.assertEqual(hits[0]["id"], "ds-enterprise-ownership")
        self.assertEqual(pr.related("the weather in Paris", s.priorities()), [])
        self.assertEqual(pr.related("", s.priorities()), [])

    def test_a_request_becomes_evidence_behind_the_priority(self) -> None:
        s = store()
        s.accrue(PRO, "2026-09")
        s.accrue(PRESS, "2026-09")
        s.submit_request(
            PRO,
            "Need subsidiary ownership for credit analysis of tribal borrowers",
            "credit analysis",
            "ds-enterprise-ownership",
        )
        s.submit_request(
            PRESS,
            "Which enterprises does each nation own; we run economic development",
            "economic development",
            "ds-enterprise-ownership",
        )
        s.submit_request(
            SEAT_2,
            "Vendor diligence on tribally owned contractors",
            "credit analysis",
            "ds-enterprise-ownership",
        )
        with self.assertRaises(pr.PointsError):
            s.submit_request(PRO, "too short", None, None)
        with self.assertRaises(pr.PointsError):
            s.submit_request(
                PRO, "a long enough request about nothing in particular", None, "no-such"
            )
        ev = s.evidence("ds-enterprise-ownership")
        self.assertEqual((ev["requests"], ev["requesting_accounts"]), (3, 2))
        self.assertEqual(ev["common_needs"], ["credit analysis", "economic development"])

    def test_the_seed_is_editorial_and_idempotent(self) -> None:
        s = store()
        n = s.seed()
        self.assertGreaterEqual(n, 11)
        s.accrue(PRO, "2026-09")
        s.allocate(PRO, "ds-enterprise-ownership", 2)
        # Re-seeding with a new status keeps the points and moves the status.
        seed = json.loads(
            (_REPO / "data" / "cedar" / "priorities.json").read_text(encoding="utf-8")
        )
        for p in seed["priorities"]:
            if p["id"] == "ds-enterprise-ownership":
                p["status"] = "data_construction_underway"
                p["evolved_from"] = "rq-tribal-enterprise-revenue"
        s.seed(seed)
        p = s.priority("ds-enterprise-ownership")
        self.assertEqual(
            (p["points"], p["status"], p["evolved_from"]),
            (2, "data_construction_underway", "rq-tribal-enterprise-revenue"),
        )
        bad = {"priorities": [{"id": "x", "type": "wish", "title": "x"}]}
        with self.assertRaises(ValueError):
            s.seed(bad)

    def test_the_seed_file_is_well_formed(self) -> None:
        seed = json.loads(
            (_REPO / "data" / "cedar" / "priorities.json").read_text(encoding="utf-8")
        )
        self.assertEqual(seed["rules"]["points_per_active_month"], pr.POINTS_PER_ACTIVE_MONTH)
        self.assertEqual(seed["rules"]["expiry_months"], pr.EXPIRY_MONTHS)
        ids = [p["id"] for p in seed["priorities"]]
        self.assertEqual(len(ids), len(set(ids)))
        for p in seed["priorities"]:
            self.assertIn(p["type"], pr.TYPES)
            self.assertIn(p.get("status", "interest"), pr.STATUSES)
            self.assertTrue(p["title"] and p["description"])
        self.assertTrue(any(p["type"] == "research_question" for p in seed["priorities"]))
        self.assertTrue(any(p["type"] == "dataset" for p in seed["priorities"]))


class TestMonths(unittest.TestCase):
    def test_month_arithmetic(self) -> None:
        self.assertEqual(pr.months_before("2026-01", 1), "2025-12")
        self.assertEqual(pr.months_before("2026-09", 12), "2025-09")
        self.assertEqual(pr.next_month("2026-12"), "2027-01")
        import datetime as dt

        self.assertEqual(pr.month_of(dt.date(2026, 9, 5)), "2026-09")


if __name__ == "__main__":
    unittest.main()
