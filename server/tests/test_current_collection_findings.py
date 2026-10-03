"""Current collection findings use served publication facts, not frozen backlog prose."""

from __future__ import annotations

import dataclasses
import unittest
from unittest.mock import patch

from cedar_press import collections as launch


class TestCurrentCollectionFindings(unittest.TestCase):
    def _needs(self, *, rows=3725, path="/owned-preview.csv", reason=None, vintage="2026"):
        owned = next(dataset for dataset in launch.LAUNCH_COLLECTION if dataset.id == "owned")
        with (
            patch.object(
                launch, "LAUNCH_COLLECTION", (dataclasses.replace(owned, vintage=vintage),)
            ),
            patch.object(launch, "collection_cedar_facts", return_value={"n_rows": rows}),
            patch.object(launch, "collection_sample", return_value={"path": path}),
            patch.object(launch, "sample_unavailable_reason", return_value=reason),
        ):
            return launch.collection_findings().needs

    def test_published_owned_listings_do_not_retain_the_old_membership_or_consent_claim(self):
        needs = self._needs()
        self.assertFalse(any(need.id.startswith("col-need-owned-") for need in needs))

    def test_zero_is_a_real_count_but_unknown_and_invalid_counts_are_not(self):
        for rows in (0, 3725):
            with self.subTest(rows=rows):
                self.assertFalse(
                    any(need.id == "col-need-owned-availability" for need in self._needs(rows=rows))
                )
        for rows in (None, True, -1, "3725", 2**53):
            with self.subTest(rows=rows):
                need = next(
                    need
                    for need in self._needs(rows=rows)
                    if need.id == "col-need-owned-availability"
                )
                self.assertIn("does not state a row count", need.text)
                self.assertNotIn("No preview", need.text)
                self.assertFalse(need.demonstration)

    def test_a_withheld_preview_keeps_its_actual_reason_without_denying_its_known_count(self):
        reason = "Only this source's unapproved private rows remain withheld."
        need = next(
            need
            for need in self._needs(path=None, reason=reason)
            if need.id == "col-need-owned-availability"
        )
        self.assertIn(reason, need.text)
        self.assertNotIn("row count", need.text)
        self.assertFalse(need.demonstration)

    def test_missing_preview_has_an_explicit_fallback(self):
        need = next(
            need for need in self._needs(path=None) if need.id == "col-need-owned-availability"
        )
        self.assertIn("No preview file is published for the current release.", need.text)

    def test_vintage_warning_tracks_absence_and_does_not_infer_periods_from_update_dates(self):
        self.assertFalse(any(need.id == "col-need-vintage" for need in self._needs()))
        for vintage in (None, "", "  "):
            with self.subTest(vintage=vintage):
                need = next(
                    need for need in self._needs(vintage=vintage) if need.id == "col-need-vintage"
                )
                self.assertTrue(need.text.startswith("No collection states a vintage."))
                self.assertIn(
                    "An update date does not establish the periods covered by every source.",
                    need.text,
                )

    def test_mixed_vintage_warning_names_only_the_collection_without_one(self):
        owned, other = launch.LAUNCH_COLLECTION[0:2]
        datasets = (
            dataclasses.replace(owned, vintage="2025"),
            dataclasses.replace(other, vintage=None),
        )
        with (
            patch.object(launch, "LAUNCH_COLLECTION", datasets),
            patch.object(launch, "collection_cedar_facts", return_value={"n_rows": 0}),
            patch.object(launch, "collection_sample", return_value={"path": "/sample.csv"}),
        ):
            need = next(
                need for need in launch.collection_findings().needs if need.id == "col-need-vintage"
            )
        self.assertIn(other.name, need.text)
        self.assertNotIn(owned.name, need.text)
        self.assertNotIn("No collection", need.text)

    def test_prototype_backlog_and_leads_are_visible_demonstrations(self):
        findings = launch.collection_findings()
        for need in findings.needs:
            if need.id in {"col-need-closing", "col-need-fy26", "col-need-matches"}:
                self.assertTrue(need.demonstration)
                self.assertTrue(need.text.startswith("Demonstration: "))
        for lead in findings.narratives:
            self.assertTrue(lead.demonstration)
            self.assertTrue(lead.name.startswith("Demonstration: "))

    def test_dated_white_earth_figure_is_not_recast_as_a_current_collection_total(self):
        figure = next(figure for figure in launch.COLLECTION_FIGURES if figure.id == "owned")
        self.assertFalse(figure.demonstration)
        self.assertEqual(figure.basis, "White Earth Nation TERO roster, supplied 2026-08-28")
        self.assertEqual([point.value for point in figure.points], [17, 4, 1])
