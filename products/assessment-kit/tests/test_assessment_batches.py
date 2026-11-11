import json

from skill_assessment import assess
from skill_assessment.cli import main
from skill_assessment.errors import IncompleteScanError


def findings(count):
    return [{'id': 'CE1', 'location': {'file': 'SKILL.md', 'start_line': 5},
             'explanation': f'Finding {i}'} for i in range(1, count + 1)]


def verdict(start, count, *, safe=True):
    return {
        'safe_to_use': safe, 'summary': 'Batch reviewed.',
        'coverage_sufficient': safe, 'coverage_reason': 'Review scope accounted for.',
        'findings': [{'index': i, 'rule_id': 'CE1',
                      'determination': 'false_positive' if safe else 'uncertain', 'reason': 'Reviewed context.'}
                     for i in range(start, start + count)],
    }


def test_batches_preserve_all_finding_identities_and_combine_judgments(skill, scanner, gateway, tmp_path):
    scanner['report']['issues'] = findings(45)
    scanner['report']['metadata']['inference_usage'] = [{'irrelevant_accounting': 'OMIT_THIS_ACCOUNTING'}]
    gateway['responses'] = [verdict(1, 20, safe=False)]
    output = tmp_path / 'reports'
    assess(skill, output)

    evidence = [json.loads(json.loads(call.data)['messages'][1]['content']) for call in gateway['calls']]
    assert [e['issue_indices'] for e in evidence] == [list(range(1, 21)), list(range(21, 41)), list(range(41, 46))]
    assert [len(e['report']['issues']) for e in evidence] == [20, 20, 5]
    assert [e['report']['issues'][0]['explanation'] for e in evidence] == ['Finding 1', 'Finding 21', 'Finding 41']
    assert all('OMIT_THIS_ACCOUNTING' not in call.data.decode() for call in gateway['calls'])
    saved = json.loads((output / 'adjudication.json').read_text())
    assert saved['status'] == 'completed'
    assert saved['safe_to_use'] is saved['coverage_sufficient'] is False
    assert [f['index'] for f in saved['findings']] == list(range(1, 46))
    assert saved['metadata']['batches_completed'] == saved['metadata']['batches_total'] == 3
    assert json.loads((output / 'skillspector.json').read_text()) == scanner['report']


def test_each_batch_can_request_files_once_and_later_batches_receive_previous_files(
    skill, scanner, gateway, tmp_path,
):
    scanner['report']['issues'] = findings(21)
    (skill / 'first.py').write_text('FIRST_BATCH_SOURCE')
    (skill / 'second.py').write_text('SECOND_BATCH_SOURCE')
    gateway['responses'] = [{'request_files': ['first.py']}, verdict(1, 20), {'request_files': ['second.py']}]
    output = tmp_path / 'reports'
    assess(skill, output)

    assert len(gateway['calls']) == 4
    third = json.loads(gateway['calls'][2].data)
    evidence = json.loads(third['messages'][1]['content'])
    assert evidence['additional_files_with_line_numbers'] == {'first.py': '1: FIRST_BATCH_SOURCE'}
    final = json.loads(gateway['calls'][3].data)
    assert json.loads(final['messages'][-1]['content'])['files'] == {'second.py': '1: SECOND_BATCH_SOURCE'}
    saved = json.loads((output / 'adjudication.json').read_text())
    assert saved['metadata']['supplied_files'] == ['SKILL.md', 'first.py', 'second.py']
    assert saved['metadata']['batches_completed'] == 2


def test_bad_later_batch_preserves_validated_findings_without_completing_assessment(
    skill, scanner, gateway, tmp_path,
):
    scanner['report']['issues'] = findings(45)
    gateway['responses'] = [verdict(1, 20), verdict(1, 20)]  # Second batch incorrectly resets indices.
    output = tmp_path / 'reports'
    try:
        assess(skill, output)
    except IncompleteScanError as error:
        assert 'Finding identity mismatch' in str(error)
        retained = error.report_dir
        saved = json.loads((retained / 'adjudication.json').read_text())
    else:
        raise AssertionError('Mismatched finding identities were accepted')
    assert not output.exists()
    assert len(gateway['calls']) == 2
    assert saved['status'] == 'failed'
    assert saved['safe_to_use'] is saved['coverage_sufficient'] is None
    assert saved['metadata']['batches_completed'] == 1
    assert [f['determination'] for f in saved['findings'][:20]] == ['false_positive'] * 20
    assert all(f['determination'] == 'not_adjudicated' for f in saved['findings'][20:])
    assert main(['summarize', '--assessment-dir', str(retained)]) == 0
