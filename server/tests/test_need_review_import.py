"""Execute the receipt-only NEED importer in a disposable fixture workspace."""

import ast
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "code" / "09_import_rulings.py"
COLUMNS = [
    "review_id",
    "queue",
    "uei",
    "cage_code",
    "entity_or_firm",
    "question",
    "YOUR_RULING",
    "YOUR_NOTE",
    "decision_id",
    "reviewer",
    "decided_at",
    "evidence_fingerprint",
    "queue_version",
    "target_cedar_uid",
    "supersedes_decision_id",
]


class TestNeedReceiptImport(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.bin"
        self.source.write_bytes(b"pinned")
        self.queue = self.root / "queue.json"
        self.queue.write_text(
            json.dumps(
                {
                    "candidate_root": str(self.root),
                    "review_id": "fixture-v1",
                    "evidence_fingerprint": "a" * 64,
                    "input_sha256": {"source.bin": hashlib.sha256(b"pinned").hexdigest()},
                    "records": [
                        {
                            "exception": True,
                            "enterprise": {
                                "enterprise_id": "CEDAR-NEST-TEST",
                                "enterprise_name": "Fixture enterprise",
                                "owner_hub_cedar_uid": "CE-HUB",
                                "enterprise_existing_cedar_uid": "CE-SELF",
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.csv = self.root / "decisions.csv"
        self.receipt = self.root / "receipt.json"
        self.row = dict.fromkeys(COLUMNS, "")
        self.row.update(
            review_id="NEED:CEDAR-NEST-TEST",
            queue="need_affiliation",
            entity_or_firm="Fixture enterprise",
            question="Affiliation?",
            YOUR_RULING="HOLD",
            YOUR_NOTE="Need evidence",
            decision_id="test-1",
            reviewer="Fixture reviewer",
            decided_at="2026-01-01T00:00:00Z",
            evidence_fingerprint="a" * 64,
            queue_version="fixture-v1",
            target_cedar_uid="CE-HUB",
        )

    def run_import(self, rows=None):
        with self.csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows or [self.row])
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(SCRIPT),
                "--need-review",
                str(self.csv),
                "--queue",
                str(self.queue),
                "--receipt-ledger",
                str(self.receipt),
            ],
            text=True,
            capture_output=True,
        )

    def test_idempotent_receipt_and_explicit_revision_preserve_hold(self):
        first = self.run_import()
        self.assertEqual(first.returncode, 0, first.stderr)
        before = self.receipt.read_bytes()
        again = self.run_import()
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn("ALREADY_RECORDED", again.stdout)
        self.assertEqual(before, self.receipt.read_bytes())
        revised = dict(
            self.row,
            decision_id="test-2",
            YOUR_RULING="SUPPORT",
            YOUR_NOTE="Explicit revised evidence judgment",
            supersedes_decision_id="test-1",
        )
        result = self.run_import([revised])
        self.assertEqual(result.returncode, 0, result.stderr)
        ledger = json.loads(self.receipt.read_text())
        self.assertEqual(
            [r["status"] for r in ledger["decisions"]], ["HELD", "RECORDED_PENDING_APPLICATION"]
        )
        self.assertEqual(ledger["decisions"][0]["decision"]["YOUR_NOTE"], "Need evidence")
        self.assertEqual(self.source.read_bytes(), b"pinned")

    def test_rejects_invalid_case_target_stale_note_name_time_and_conflicts(self):
        self.assertEqual(self.run_import().returncode, 0)
        before = self.receipt.read_bytes()
        changes = [
            {"target_cedar_uid": "CE-SELF"},
            {"review_id": "NEED:UNKNOWN"},
            {"evidence_fingerprint": "b" * 64},
            {"queue_version": "old"},
            {"YOUR_NOTE": ""},
            {"entity_or_firm": "Wrong name"},
            {"decided_at": "2999-01-01T00:00:00Z"},
            {"decided_at": "2026-01-01"},
            {"YOUR_RULING": "REJECT"},
            {"decision_id": "another-id"},
            {"decision_id": "another-id", "supersedes_decision_id": "unknown"},
        ]
        for change in changes:
            with self.subTest(change=change):
                result = self.run_import([dict(self.row, **change)])
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(before, self.receipt.read_bytes())
        self.source.write_bytes(b"changed")
        result = self.run_import()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Stale queue input", result.stderr)
        self.assertEqual(before, self.receipt.read_bytes())

    def test_legacy_inbox_refuses_need_before_reading_canonical_ledger(self):
        path = self.root / "rulings_inbox_fixture.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerow(self.row)
        spec = importlib.util.spec_from_file_location("need_receipt_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(module, "REVIEW", self.root), patch.object(module, "load_base") as load:
            with self.assertRaisesRegex(SystemExit, "legacy propagation refused"):
                module.main(dry_run=True)
            load.assert_not_called()

    def test_field_ruling_and_conflicting_batch_are_not_applied(self):
        field = dict(
            self.row,
            review_id="NEED:enterprise_existing_cedar_uid",
            queue="need_field",
            target_cedar_uid="",
            entity_or_firm="enterprise_existing_cedar_uid",
            YOUR_RULING="INTERNAL_ONLY",
            decision_id="field-1",
        )
        result = self.run_import([field, dict(field, YOUR_RULING="PUBLISH_CURRENT")])
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.receipt.exists())
        result = self.run_import([field])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["applied"])
        self.assertIn("RECORDED_PENDING_APPLICATION", result.stdout)


class TestNeedReviewBrowserState(unittest.TestCase):
    """Run the actual generated JavaScript, with browser I/O represented in memory."""

    def test_reload_exports_recovery_history_and_async_copy_race(self):
        module = ast.parse((ROOT / "code" / "08_build_review_page.py").read_text(encoding="utf-8"))
        template = next(
            ast.literal_eval(node.value)
            for node in module.body
            if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "NEED_REVIEW_HTML" for t in node.targets)
        )
        payload = {
            "review_id": "fixture-v1",
            "evidence_fingerprint": "a" * 64,
            "input_sha256": {},
            "records": [
                {
                    "enterprise": {
                        "enterprise_id": "CEDAR-NEST-TEST",
                        "enterprise_name": "Fixture",
                        "owner_hub_name": "Fixture hub",
                        "owner_hub_cedar_uid": "CE-HUB",
                    },
                    "register_target": {"canonical_name": "Fixture", "entity_class": "Test"},
                    "formal_relationships": [],
                    "constellation_evidence": [],
                }
            ],
        }
        script = template.split("<script>", 1)[1].split("</script>", 1)[0]
        script = script.replace("__NEED_DATA__", json.dumps(payload))
        harness = r"""
const vm=require('node:vm'),assert=require('node:assert/strict');
const source=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
let id=0;
function browser(storage=new Map()){
 const elements=new Map(),events={},downloads=[];
 function element(){return {value:'',textContent:'',hidden:false,classList:{toggle(){}},
  appendChild(){},addEventListener(name,fn){this[name]=fn;},focus(){},select(){},
  click(){if(this.download)downloads.push(this.download);else if(this.onclick)this.onclick();}};}
 const document={getElementById(id){if(!elements.has(id))elements.set(id,element());
 return elements.get(id);},
 createElement:element};
 const window={addEventListener(name,fn){events[name]=fn;}};
 const context={document,window,
 localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},
  navigator:{clipboard:{writeText:async()=>{}}},crypto:{randomUUID:()=>`fixture-${++id}`},
  alert(message){throw Error(message);},Blob,
 URL:{createObjectURL:()=>"blob:fixture",revokeObjectURL(){}},setTimeout(){}};
 vm.createContext(context);vm.runInContext(source,context);
 return {context,storage,downloads,events,get:id=>document.getElementById(id),
   run:code=>vm.runInContext(code,context),api:window.needReview};
}
(async()=>{
 let b=browser();const field='NEED:enterprise_existing_cedar_uid',row='NEED:CEDAR-NEST-TEST';
 b.get('reviewer').value='Fixture reviewer';
 b.run(`draft(${JSON.stringify(field)},{note:'Keep internal'});
 resolve(${JSON.stringify(field)},'INTERNAL_ONLY');`);
 b.run(`draft(${JSON.stringify(row)},{note:'Reject, with "quoted" evidence\\nand a second line'});
 resolve(${JSON.stringify(row)},'REJECT');`);
 assert.equal(b.api.exportStatus().pending,2);
 assert.match(b.get('exportwarning').textContent,/newer than the last export/);
 const stored=b.storage;
 b=browser(stored);assert.equal(b.api.counts().events,2);assert.match(b.api.csv(),/second line/);
 assert.match(b.get('topstatus').textContent,
 /2 of 2 decisions saved locally; 0 of 2 history entries exported/);
 b.get('complete').onclick();assert.equal(b.downloads[0],'cedar_need_decisions.csv');
 assert.equal(b.api.exportStatus().pending,0);
 b=browser(stored);assert.equal(b.api.exportStatus().exported,2);
 const csv=b.api.csv();let receipt=b.api.importDecisions(csv);
 assert.equal(receipt.imported,0);assert.equal(receipt.duplicate,2);assert.equal(b.api.counts().events,2);
 b.get('reviewer').value='Fixture reviewer';
 b.run(`draft(${JSON.stringify(row)},{note:'Revised to HOLD with retained evidence'});
 resolve(${JSON.stringify(row)},'HOLD');`);
 assert.equal(b.api.counts().events,3);assert.equal(b.api.exportStatus().pending,1);
 assert.match(b.api.csv(),/Reject, with/);assert.match(b.api.csv(),/Revised to HOLD/);
 b.run(`draft(${JSON.stringify(row)},{note:'Unfinished research note'});`);
 assert.equal(b.api.exportStatus().drafts,1);
 let warned=false;b.events.beforeunload({preventDefault(){warned=true;}});assert.equal(warned,true);
 const backup=b.api.recovery();b.get('recover').onclick();
 assert.equal(b.downloads.at(-1),'cedar_need_review_recovery.json');
 const fresh=browser();receipt=fresh.api.importRecovery(backup);
 assert.equal(receipt.imported,3);assert.equal(fresh.api.counts().events,3);
 assert.equal(fresh.get('note-'+row).value,'Unfinished research note');
 receipt=fresh.api.importRecovery(backup);assert.equal(receipt.duplicate,3);
 assert.equal(fresh.api.counts().events,3);assert.match(fresh.api.csv(),/Reject, with/);
 const before=fresh.api.recovery();const invalid=JSON.parse(backup);
 invalid.evidence_fingerprint='old';
 assert.throws(()=>fresh.api.importRecovery(JSON.stringify(invalid)),/Stale/);
 assert.equal(fresh.api.recovery(),before);
 // A clipboard promise must not mark decisions added during the wait as exported.
 let copied;fresh.context.navigator.clipboard.writeText=()=>new Promise(resolve=>{copied=resolve;});
 const copying=fresh.get('copy').onclick();fresh.get('reviewer').value='Fixture reviewer';
 fresh.run(`draft(${JSON.stringify(row)},{note:'New rejection'});
 resolve(${JSON.stringify(row)},'REJECT');`);
 copied();await copying;assert.equal(fresh.api.exportStatus().pending,1);
 // Failed downloads keep pending work and expose the complete copyable payload.
 fresh.context.URL.createObjectURL=()=>{throw Error('download blocked');};
 fresh.get('download').onclick();assert.equal(fresh.api.exportStatus().pending,1);
 assert.match(fresh.get('payload').value,/New rejection/);
 assert.match(fresh.get('receipt').textContent,/Download failed/);
 process.stdout.write('reload, completion export, recovery, revisions, '+
 'duplicate import and export races passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
"""
        result = subprocess.run(
            ["node", "-e", harness],
            input=json.dumps(script),
            text=True,
            capture_output=True,
            cwd=ROOT,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("export races passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
