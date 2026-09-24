"""Fixture-only regression for nonprofit identity holds across both producers."""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def module(filename):
    spec = importlib.util.spec_from_file_location(filename[:-3], ROOT / 'code' / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class NonprofitRulingPrecedenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = module('174_apply_rulings_to_source_tables.py')
        cls.producer = module('70_key_unjoined_datasets.py')
        cls.hub = module('167_link_nonprofit_family_via_ein_hub.py')

    def ruling(self, outcome='UNRESOLVED_ENTITY', target='', status='SETTLED'):
        return dict(subject_key='EIN:453221112', status=status, outcome=outcome,
                    source_file='fixture.csv', ruling='NATIVE_ORG', ruling_date='2026-09-02',
                    confidence_tier='A', resolved_tribe_id=target,
                    resolved_canonical_name='Ahtna, Incorporated' if target else '',
                    tier_source='stated_on_ruling_row')

    def org(self):
        return dict(EIN='453221112', org_name='Ahtna Intertribal Resource Commission',
                    state='AK', tribe_id='ANRC-AHTNAI-00', entity_tier='B',
                    entity_match_method='containment', entity_match_basis='resolver_containment',
                    cedar_uid='CE-00076-76', disposition='NATIVE_VERIFIED_STRICT',
                    evidence='preserved source evidence', entity_id='',
                    cedar_spine_entity_id='ANRC-AHTNAI-00')

    def test_hold_is_not_native_exclusion_and_is_idempotent(self):
        rows = [self.org()]
        rules = [self.ruling()]
        p = self.producer
        with patch.object(p, 'rd', side_effect=lambda path: rules if path.name == 'cedar_ruling_ledger_consolidated.csv' else rows), \
                patch.object(p, 'ledger_negative_ein_rulings', return_value={}), \
                patch.object(p, 'load_ruling_gate', return_value=self.gate), \
                patch.object(p, 'key_name', side_effect=AssertionError('held EIN reached resolver')), \
                patch.object(p, 'rewrite_in_place'), patch.object(p, 'show', return_value={}):
            p.do_np_orgs()
            first = copy.deepcopy(rows)
            p.do_np_orgs()
        self.assertEqual(first, rows)
        self.assertEqual(rows[0]['EIN'], '453221112')
        self.assertEqual(rows[0]['disposition'], 'NATIVE_VERIFIED_STRICT')
        self.assertEqual(rows[0]['evidence'], 'preserved source evidence')
        for key in ('tribe_id', 'entity_id', 'cedar_uid', 'cedar_spine_entity_id'):
            self.assertEqual(rows[0][key], '')
        self.assertNotEqual(rows[0]['entity_tier'], 'X')

    def candidates(self, rules):
        h = self.hub
        bridge = [dict(ein='453221112', uei='J9NAVAM9B1J3')]
        ledger = [dict(identifier_type='UEI', identifier='J9NAVAM9B1J3',
                       tribe_id='ANRC-AHTNAI-00', confidence_tier='B', attribution_method='need_v6')]
        with patch.object(h, 'NP_ORGS', [self.org()]), patch.object(h, 'LEDGER', ledger), \
                patch.object(h, 'rd', side_effect=lambda path: bridge if path.name == 'np_ein_uei_bridge.csv' else []):
            return h.build_hub({'ANRC-AHTNAI-00': {}}, self.gate.build_decisions(rules), self.gate)

    def test_hub_blocks_both_containment_and_inherited_route(self):
        self.assertEqual(dict(self.candidates([self.ruling()])), {})

    def test_current_affirmative_decision_allows_same_target(self):
        # Supersession belongs to the consolidated ledger, not date guessing here.
        result = self.candidates([self.ruling('ENTITY', 'ANRC-AHTNAI-00')])
        self.assertEqual({r['source'] for r in result['453221112']},
                         {'np_orgs', 'ein_uei_bridge_to_ledger'})

    def test_conflict_blocks_both_routes(self):
        self.assertEqual(dict(self.candidates([self.ruling(status='CONFLICT_NOT_APPLIED')])), {})

    def test_affirmative_other_target_cannot_be_overridden(self):
        self.assertEqual(dict(self.candidates([self.ruling('ENTITY', 'DISTINCT-INTERTRIBAL')])), {})

    def test_propagation_hold_precedes_stale_hub_and_name_fallback(self):
        row = self.org()
        decisions = self.gate.build_decisions([self.ruling()])
        with patch.object(self.hub, 'deterministic_name_match', side_effect=AssertionError('fallback ran')):
            result = self.hub.apply_nonprofit_link(
                row, 'cedar_', row['EIN'], namecol='org_name',
                hub={'453221112': {'entity_id': 'ANRC-AHTNAI-00'}}, excl={},
                ruling_gate=self.gate, decisions=decisions, org_identity=True)
        self.assertEqual(result, 'identity_held')
        self.assertEqual(row['cedar_uid'], '')
        self.assertEqual(row['entity_match_method'], '')
        self.assertEqual(row['disposition'], 'NATIVE_VERIFIED_STRICT')

    def test_affirmative_target_cannot_be_replaced_by_name_fallback(self):
        row = self.org()
        decisions = self.gate.build_decisions([self.ruling('ENTITY', 'DISTINCT-INTERTRIBAL')])
        with patch.object(self.hub, 'deterministic_name_match', return_value=('ANRC-AHTNAI-00', 'Ahtna', 'containment')):
            result = self.hub.apply_nonprofit_link(
                row, 'cedar_', row['EIN'], namecol='org_name', hub={}, excl={},
                ruling_gate=self.gate, decisions=decisions, org_identity=True)
        self.assertEqual(result, 'identity_held')
        self.assertEqual(row['cedar_spine_entity_id'], '')

    def test_affirmative_target_cannot_be_replaced_by_stale_hub(self):
        row = self.org()
        decisions = self.gate.build_decisions([self.ruling('ENTITY', 'DISTINCT-INTERTRIBAL')])
        result = self.hub.apply_nonprofit_link(
            row, 'cedar_', row['EIN'], hub={'453221112': {'entity_id': 'ANRC-AHTNAI-00'}},
            excl={}, ruling_gate=self.gate, decisions=decisions, org_identity=True)
        self.assertEqual(result, 'identity_held')
        self.assertEqual(row['cedar_uid'], '')

    def test_hold_preserves_opposite_role_and_issued_ids(self):
        row = dict(cedar_uid='CE-OTHER', entity_id='SOURCE-OBJECT', object_id='FILING-1',
                   flow_id='FLOW-1', cedar_recipient_spine_entity_id='RECIPIENT',
                   cedar_filer_spine_entity_id='WRONG-FILER', EIN='453221112')
        decisions = self.gate.build_decisions([self.ruling()])
        self.hub.apply_nonprofit_link(row, 'cedar_filer_', row['EIN'],
                                     hub={}, excl={}, ruling_gate=self.gate, decisions=decisions)
        self.assertEqual(row['cedar_filer_spine_entity_id'], '')
        for key, value in [('cedar_uid', 'CE-OTHER'), ('entity_id', 'SOURCE-OBJECT'),
                           ('object_id', 'FILING-1'), ('flow_id', 'FLOW-1'),
                           ('cedar_recipient_spine_entity_id', 'RECIPIENT')]:
            self.assertEqual(row[key], value)

    def test_blank_ein_never_looks_up_empty_key(self):
        self.assertEqual(self.gate.nonprofit_identity_hold('', {'EIN:': {'action': 'RULING_CONFLICT'}}), '')

    def test_blank_ein_keeps_existing_name_fallback(self):
        row = {'org_name': 'Independent organization'}
        with patch.object(self.hub, 'deterministic_name_match', return_value=('', '', 'no_spine_match')) as matcher:
            self.hub.apply_nonprofit_link(row, 'cedar_', '', namecol='org_name',
                                         hub={}, excl={}, ruling_gate=self.gate,
                                         decisions={'EIN:': {'action': 'RULING_CONFLICT'}})
        matcher.assert_called_once()

    def test_ein_formats_and_malformed_raw_propagation(self):
        decisions = self.gate.build_decisions([self.ruling()])
        self.assertEqual(self.gate.nonprofit_identity_hold('45-3221112', decisions),
                         self.gate.nonprofit_identity_hold('453221112', decisions))
        for raw in ['EIN453221112', '45322111', '45/3221112']:
            self.assertEqual(self.gate.nonprofit_identity_hold(raw, decisions), 'INVALID_EIN')
            with patch.object(self.hub, 'deterministic_name_match', side_effect=AssertionError('malformed fallback')):
                result = self.hub.apply_nonprofit_link({}, 'cedar_', raw, namecol='org_name',
                                                     hub={}, excl={}, ruling_gate=self.gate, decisions={})
            self.assertEqual(result, 'identity_held')

    def test_member_evidence_does_not_supply_identity(self):
        decisions = self.gate.build_decisions([self.ruling()])
        row = self.org()
        row['relationship_evidence'] = 'Ahtna Incorporated is a member of AITRC'
        self.gate.clear_nonprofit_identity(row)
        self.assertTrue(self.gate.nonprofit_identity_hold(row['EIN'], decisions))
        self.assertEqual(row['relationship_evidence'], 'Ahtna Incorporated is a member of AITRC')


if __name__ == '__main__':
    unittest.main()
