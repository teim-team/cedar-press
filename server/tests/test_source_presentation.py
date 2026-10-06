"""Citation display preserves authority, timing and unresolved source gaps."""

import unittest

from cedar_press.source_presentation import present, safe_url


class SourcePresentationTest(unittest.TestCase):
    def test_original_document_hash_never_comes_from_the_ingestion_file_hash(self):
        row = {
            "source_document_sha256": "a" * 64,
            "source_retrieved_date": "2026-09-27",
            "sha256": "b" * 64,
            "source_inbox": "D:/private/extract.csv",
        }
        value = present("foundation-corporate-giving", row)
        self.assertEqual(value["originalDocumentSha256"], "a" * 64)
        self.assertEqual(value["retrievedDate"], "2026-09-27")
        row["source_document_sha256"] = "not a document hash"
        self.assertIsNone(present("foundation-corporate-giving", row)["originalDocumentSha256"])
        self.assertIsNone(present("contractors", row)["originalDocumentSha256"])
        self.assertNotIn("private", str(value))

    def test_official_host_fallback_is_exact_and_preserves_date_meaning(self):
        row = {
            "source_url": "https://www.federalregister.gov/d/2014-09591",
            "notice_date": "2025-03-01",
        }
        value = present("federal-register", row)
        self.assertIn("Office of the Federal Register", value["publisher"])
        self.assertIsNone(value["title"])
        self.assertEqual(value["publicationDate"], "2025-03-01")
        row["agency_names"] = "Bureau of Indian Affairs"
        self.assertEqual(
            present("federal-register", row)["issuingAuthority"], "Bureau of Indian Affairs"
        )
        self.assertEqual(present("federal-register", row)["publisher"], value["publisher"])
        row["source_url"] = "https://www.federalregister.gov.example.org/d/2014-09591"
        self.assertIsNone(present("federal-register", row)["publisher"])
        row.update(
            source_system="Federal Register",
            publication_date="2026-03-01",
            effective_date="2026-04-01",
        )
        self.assertEqual(present("federal-register", row)["publicationDate"], "2026-03-01")

    def test_ingest_files_are_not_publishers(self):
        value = present(
            "deals",
            {
                "source_system": "clean.csv",
                "source_files": "D:/private/data.csv",
                "title": "Cedar event description",
                "source_url": "https://tribe.org/announcement",
            },
        )
        self.assertIsNone(value["publisher"])
        self.assertIn("Original publisher", value["gaps"][0])
        self.assertEqual(value["titleBasis"], "Cedar event description")
        self.assertNotIn("clean.csv", str(value))
        self.assertNotIn("private", str(value))

    def test_govinfo_keeps_action_and_introduction_distinct(self):
        value = present(
            "legislation",
            {
                "source_system": "govinfo.gov",
                "title": "Example bill",
                "bill_id": "119-s-254",
                "source_url": "https://www.govinfo.gov/app/details/PLAW-119publ99",
                "introduced_date": "2025-01-24",
                "latest_action_date": "2026-06-12",
            },
        )
        self.assertIn("Government Publishing Office", value["publisher"])
        self.assertEqual(
            value["eventDates"],
            {"introduced_date": "2025-01-24", "latest_action_date": "2026-06-12"},
        )
        self.assertIsNone(value["publicationDate"])

    def test_gaming_publisher_does_not_replace_exact_issuer(self):
        row = {
            "source_authority": (
                "Federal Audit Clearinghouse (GSA), reporting package as submitted by the auditee"
            ),
            "filer_or_issuer_name": "Exact legal issuer",
            "source_url": "https://www.fac.gov/example",
            "period_end": "2025-09-30",
            "source_date": "2026-02-01",
            "source_document": "extract.csv",
        }
        self.assertIsNone(present("gaming", row))
        value = present("gaming", row, "gaming_financial_disclosures")
        self.assertEqual(value["publisher"], row["source_authority"])
        self.assertIsNone(value["title"])
        self.assertIsNone(value["publicationDate"])
        self.assertEqual(value["reportingPeriod"]["period_end"], "2025-09-30")
        self.assertNotIn("Exact legal issuer", value["citation"])

    def test_explicit_fr_link_does_not_change_bia_publisher(self):
        value = present(
            "gaming",
            {
                "source_url": "",
                "fr_notice_url": "https://www.federalregister.gov/documents/2002/09/17/02-23597/indian-gaming",
                "bia_title": "Indian gaming compact",
                "source_system": "bia_oig_compact_index",
            },
            "gaming_compact_versions",
        )
        self.assertTrue(value["publisher"].startswith("Bureau of Indian Affairs"))
        self.assertTrue(value["url"].startswith("https://www.federalregister.gov/"))

    def test_held_rows_cite_their_source_and_unknown_systems_are_not_promoted(self):
        # Owner ruling 2026-10-04: a held or rights-status row keeps its source
        # citation; the status is provenance.
        self.assertIsNotNone(
            present("gaming", {"publication_status": "held_identity"}, "gaming_compacts")
        )
        self.assertIsNone(
            present("gaming", {"source_system": "vendor_file.csv"}, "gaming_regulatory_events")[
                "publisher"
            ]
        )
        self.assertIsNone(
            present("gaming", {"source_authority": "extract.csv"}, "gaming_financial_disclosures")[
                "publisher"
            ]
        )

    def test_nonpublic_and_credential_links_are_omitted(self):
        for url in [
            "https://name:secret@example.org/report",
            "https://localhost/report",
            "file:///private/report",
            "https://agency.gov/report?X-Amz-Signature=private",
            "https://127.0.0.1/report",
        ]:
            with self.subTest(url=url):
                self.assertIsNone(safe_url(url))
