import json
import urllib.request

import pytest
from skill_assessment import assess
from skill_assessment.errors import IncompleteScanError, ScanError


def test_public_assess_reviews_requested_files_together_and_reuses_the_pair(skill, scanner, gateway, tmp_path):
    (skill / 'run.py').write_text('print("safe example")\n')
    (skill / 'reference.md').write_text('Context for the example.\n')
    (skill / 'unrequested.txt').write_text('UNREQUESTED_CONTENT')
    gateway['responses'] = [{'request_files': ['run.py', 'reference.md']}]
    gateway['usage'] = {'prompt_tokens': 100, 'completion_tokens': 30, 'total_tokens': 130}
    output = tmp_path / 'reports'

    assert assess(skill, output) == output
    assert len(scanner['calls']) == 1
    assert len(gateway['calls']) == 2
    first, second = (json.loads(call.data) for call in gateway['calls'])
    evidence = json.loads(first['messages'][1]['content'])
    assert set(evidence['file_inventory']) == {'SKILL.md', 'run.py', 'reference.md', 'unrequested.txt'}
    assert 'safe example' not in gateway['calls'][0].data.decode()
    supplied = json.loads(second['messages'][-1]['content'])['files']
    assert supplied == {'run.py': '1: print("safe example")', 'reference.md': '1: Context for the example.'}
    assert 'UNREQUESTED_CONTENT' not in gateway['calls'][1].data.decode()
    verdict = json.loads((output / 'adjudication.json').read_text())
    assert verdict['status'] == 'completed'
    assert verdict['metadata']['supplied_files'] == ['SKILL.md', 'reference.md', 'run.py']
    assert verdict['metadata']['calls_attempted'] == verdict['metadata']['calls_succeeded'] == 2
    assert verdict['metadata']['token_usage'] == {'prompt_tokens': 200, 'completion_tokens': 60, 'total_tokens': 260}
    assert json.loads((output / 'skillspector.json').read_text()) == scanner['report']
    assert assess(skill, output, if_changed=True) == output
    assert len(gateway['calls']) == 2


@pytest.mark.parametrize('requested', [['../outside.txt'], ['/etc/passwd'], ['missing.txt'], ['link.txt']])
def test_rejects_unlisted_or_symlink_files_without_another_request(skill, scanner, gateway, tmp_path, requested):
    outside = tmp_path / 'outside.txt'
    outside.write_text('OUTSIDE_CONTENT')
    (skill / 'link.txt').symlink_to(outside)
    gateway['responses'] = [{'request_files': requested}]
    output = tmp_path / 'reports'

    with pytest.raises(IncompleteScanError):
        assess(skill, output)

    assert not output.exists()
    assert len(gateway['calls']) == 1
    assert 'OUTSIDE_CONTENT' not in gateway['calls'][0].data.decode()
    saved = json.loads(next(tmp_path.glob('my-skill-*/adjudication.json')).read_text())
    assert saved['status'] == 'failed'
    assert saved['safe_to_use'] is None


def test_second_file_request_fails_without_a_third_model_call(skill, scanner, gateway, tmp_path):
    (skill / 'run.py').write_text('print("example")')
    gateway['responses'] = [{'request_files': ['run.py']}, {'request_files': ['SKILL.md']}]
    with pytest.raises(IncompleteScanError):
        assess(skill, tmp_path / 'reports')
    assert len(gateway['calls']) == 2


def test_old_review_scope_is_not_reused_as_expanded_review(skill, scanner, gateway, tmp_path):
    output = tmp_path / 'reports'
    assess(skill, output)
    path = output / 'adjudication.json'
    verdict = json.loads(path.read_text())
    verdict['scope'] = 'MVP: examines SKILL.md and scanner evidence only.'
    path.write_text(json.dumps(verdict))
    assess(skill, output, if_changed=True)
    assert len(scanner['calls']) == 2
    assert len(gateway['calls']) == 2


def test_source_changed_during_review_does_not_replace_previous_assessment(
    skill, scanner, gateway, tmp_path, monkeypatch,
):
    output = tmp_path / 'reports'
    assess(skill, output)
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    original = urllib.request.OpenerDirector.open

    def complete(opener, request, **kwargs):
        response = original(opener, request, **kwargs)
        (skill / 'SKILL.md').write_text('Changed during assessment')
        return response

    monkeypatch.setattr(urllib.request.OpenerDirector, 'open', complete)
    with pytest.raises(ScanError):
        assess(skill, output)
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before


def test_symlink_manifest_cannot_change_the_assessment_root(skill, scanner, gateway, tmp_path):
    from skill_assessment.errors import InvalidSkillDirectoryError

    outside = tmp_path / 'outside'
    outside.mkdir()
    manifest = skill / 'SKILL.md'
    (outside / 'SKILL.md').write_bytes(manifest.read_bytes())
    manifest.unlink()
    manifest.symlink_to(outside / 'SKILL.md')
    with pytest.raises(InvalidSkillDirectoryError):
        assess(skill, tmp_path / 'reports')
    assert not scanner['calls']
    assert not gateway['calls']
