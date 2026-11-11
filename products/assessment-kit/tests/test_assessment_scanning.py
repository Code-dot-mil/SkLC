import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import mock_open

import pytest
from skill_assessment.cli import main
from skill_assessment.errors import (
    IncompleteScanError,
    MissingFrontmatterError,
    OutputDirectoryError,
    ScanError,
    ScanTimeoutError,
)
from skill_assessment.scanning import scan_skill


@pytest.mark.parametrize(("options", "timeout"), [([], 600), (["--timeout", "120"], 120)])
def test_cli_applies_scanner_timeout(skill, scanner, tmp_path, options, timeout):
    code = main(["assess", "--skill", str(skill), "--output-dir", str(tmp_path / "reports"), *options])

    assert code == 0
    assert scanner["timeouts"] == [timeout]


@pytest.mark.parametrize("timeout", ["0", "-1", "1.5", "invalid"])
def test_cli_rejects_invalid_timeout_before_scanning(skill, scanner, tmp_path, timeout):
    output = tmp_path / "reports"

    with pytest.raises(SystemExit) as error:
        main(["assess", "--skill", str(skill), "--output-dir", str(output / "current"), "--timeout", timeout])

    assert error.value.code == 2
    assert not scanner["calls"]
    assert not output.exists()


@pytest.mark.parametrize("failure", [
    "process", "missing", "malformed", "execution",
    "unavailable", "degraded", "lost-calls", "mode", "timeout",
])
def test_failed_scans_retain_artifacts_and_never_retry(skill, scanner, tmp_path, failure):
    # Arrange
    expected_error = IncompleteScanError
    report = scanner["report"]
    if failure in ("process", "missing", "malformed", "execution", "timeout"):
        expected_error = ScanError
    if failure == "process":
        scanner["status"] = 2
    elif failure == "missing":
        scanner["report"] = None
    elif failure == "malformed":
        scanner["report"] = ["unexpected report shape"]
    elif failure == "execution":
        report["execution_successful"] = False
    elif failure == "unavailable":
        report["metadata"]["llm_available"] = False
    elif failure == "degraded":
        report["metadata"]["llm_degraded"] = True
    elif failure == "lost-calls":
        report["metadata"].update(llm_calls_attempted=2, llm_calls_succeeded=1)
    elif failure == "mode":
        report["metadata"]["llm_requested"] = False
    elif failure == "timeout":
        expected_error = ScanTimeoutError
        scanner["error"] = subprocess.TimeoutExpired("skillspector", 300)
    output = tmp_path / "retained"

    # Act
    with pytest.raises(expected_error) as error:
        scan_skill(skill, output)
    code = main(["assess", "--skill", str(skill), "--output-dir", str(output / "current")])

    # Assert
    assert code == 3
    assert error.value.report_dir.parent == output
    assert len(scanner["calls"]) == 2  # One attempt per public invocation; no static retry.
    assert all("--no-llm" not in command for command in scanner["calls"])
    runs = list(output.iterdir())
    assert len(runs) == 2
    for run in runs:
        assert (run / "scanner.log").read_text()
        path = run / "skillspector.json"
        if scanner["report"] is None:
            assert not path.exists()
        else:
            assert json.loads(path.read_text()) == scanner["report"]
        adjudication = json.loads((run / "adjudication.json").read_text())
        if failure in ("process", "missing", "malformed", "execution", "timeout"):
            assert adjudication["status"] == "unavailable"
            assert adjudication["safe_to_use"] is None
        else:
            assert adjudication["status"] == "completed"


@pytest.mark.parametrize("invalid_skill", [False, True])
def test_rejects_invalid_input_before_writing_or_scanning(skill, scanner, invalid_skill):
    # Arrange
    expected_error = OutputDirectoryError
    if invalid_skill:
        (skill / "SKILL.md").write_text("No frontmatter")
        expected_error = MissingFrontmatterError
    before = (skill / "SKILL.md").read_bytes()
    output = skill / "reports"

    # Act
    with pytest.raises(expected_error):
        scan_skill(skill, output)
    code = main(["assess", "--skill", str(skill), "--output-dir", str(output / "current")])

    # Assert
    assert code == 1
    assert not scanner["calls"]
    assert not output.exists()
    assert (skill / "SKILL.md").read_bytes() == before


def test_rejects_multiple_skills_before_scanning(skill, scanner, tmp_path):
    # Arrange
    args = ["assess", "--skill", str(skill), "--skill", str(skill), "--output-dir", str(tmp_path / "reports")]

    # Act
    with pytest.raises(SystemExit) as error:
        main(args)

    # Assert
    assert error.value.code == 2
    assert not scanner["calls"]


def test_output_setup_failure_preserves_existing_file(skill, scanner, tmp_path):
    # Arrange
    output = tmp_path / "reports"
    output.write_bytes(b"existing file")
    before = (skill / "SKILL.md").read_bytes()

    # Act
    with pytest.raises(OutputDirectoryError):
        scan_skill(skill, output)
    code = main(["assess", "--skill", str(skill), "--output-dir", str(output / "current")])

    # Assert
    assert code == 1
    assert not scanner["calls"]
    assert output.read_bytes() == b"existing file"
    assert (skill / "SKILL.md").read_bytes() == before


@pytest.mark.parametrize("failure", ["open", "close"])
def test_diagnostic_storage_failure_is_an_output_error(skill, scanner, tmp_path, monkeypatch, failure):
    # Arrange: filesystem faults are injected at the diagnostic file boundary.
    monkeypatch.setenv("PATH", "")
    output = tmp_path / "reports"
    before = (skill / "SKILL.md").read_bytes()
    original_open = Path.open
    log = mock_open()
    if failure == "open":
        log.side_effect = PermissionError("storage unavailable")
    else:
        log.return_value.__exit__.side_effect = OSError("storage unavailable")

    def open_file(path, *args, **kwargs):
        return log(*args, **kwargs) if path.name == "scanner.log" else original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open_file)

    # Act
    with pytest.raises(OutputDirectoryError):
        scan_skill(skill, output)
    code = main(["assess", "--skill", str(skill), "--output-dir", str(output / "current")])

    # Assert
    assert code == 1
    assert (skill / "SKILL.md").read_bytes() == before


@pytest.mark.skipif(shutil.which("skillspector") is None, reason="external SkillSpector prerequisite is not installed")
def test_real_static_scan_provides_actionable_findings(skill, tmp_path):
    # Arrange
    script = skill / "run.py"
    script.write_text("eval(input('Expression: '))\n")
    before = {path.name: path.read_bytes() for path in skill.iterdir()}
    output = tmp_path / "reports"

    # Act
    code = main(["assess", "--skill", str(skill), "--scan-mode", "static-only",
                 "--output-dir", str(output / "current")])

    # Assert
    assert code == 0
    report = json.loads(next(output.glob("*/skillspector.json")).read_text())
    assert report["metadata"]["llm_requested"] is False
    findings = [issue for issue in report["issues"] if issue["location"]["file"].endswith("run.py")]
    assert findings
    assert all(issue["explanation"] and issue["remediation"] for issue in findings)
    assert {path.name: path.read_bytes() for path in skill.iterdir()} == before


def test_missing_scanner_fails_without_creating_output(skill, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PATH", "")
    before = set(tmp_path.rglob("*"))
    output = tmp_path / "new" / "reports"

    with pytest.raises(ScanError) as error:
        scan_skill(skill, output)
    assert error.value.report_dir is None
    assert main(["assess", "--skill", str(skill), "--output-dir", str(output)]) == 3

    assert "SkillSpector" in capsys.readouterr().err
    assert set(tmp_path.rglob("*")) == before


def test_assessment_uses_external_scanner_on_path(skill, tmp_path, monkeypatch):
    # Arrange: a standalone executable provides the scanner's public CLI contract.
    scanner_bin = tmp_path / "bin"
    scanner_bin.mkdir()
    executable = scanner_bin / "skillspector"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import json, sys\n"
        "from pathlib import Path\n"
        "if sys.argv[1] == '--version': print('SkillSpector v2.11.2'); sys.exit(0)\n"
        "assert sys.argv[1] == 'scan' and '--no-llm' in sys.argv\n"
        "report = {'execution_successful': True, 'analysis_completeness': {'is_complete': True}, "
        "'metadata': {'llm_requested': False}, 'issues': []}\n"
        "Path(sys.argv[sys.argv.index('--output') + 1]).write_text(json.dumps(report))\n"
        "print('external scanner completed')\n"
    )
    executable.chmod(0o755)
    monkeypatch.setenv("PATH", str(scanner_bin))
    output = tmp_path / "reports"

    # Act
    code = main(["assess", "--skill", str(skill), "--scan-mode", "static-only",
                 "--output-dir", str(output / "current")])

    # Assert
    assert code == 0
    report_path = next(output.glob("*/skillspector.json"))
    assert json.loads(report_path.read_text())["execution_successful"] is True
    assert report_path.with_name("scanner.log").stat().st_size > 0


def test_adjudicates_partial_report_with_full_skill_context(skill, scanner, gateway, tmp_path):
    scanner['report']['analysis_completeness'].update(
        is_complete=False, status='partial', coverage_percent=100,
        ledger_exceptions=[{'outcome': 'partial', 'phase': 'reference_resolution',
                            'reason_code': 'reference_unresolved', 'start_line': 5, 'fatal': False}],
        references=[{'evidence': 'Authn/authz checks', 'status': 'missing'}],
    )
    scanner['report']['issues'][0].update(tags=['llm-unconfirmed', 'likely-benign-context'], confidence=0.9)
    # Repeated rule IDs must remain distinct findings.
    scanner['report']['issues'].append(dict(scanner['report']['issues'][0], finding_id='another-finding'))
    (skill / 'private.py').write_text('DO_NOT_TRANSMIT_THIS_FILE')
    output = tmp_path / 'reports'

    assert main(['assess', '--skill', str(skill), '--output-dir', str(output / "current")]) == 0

    raw = next(output.glob('*/skillspector.json'))
    assert json.loads(raw.read_text()) == scanner['report']
    result = json.loads(raw.with_name('adjudication.json').read_text())
    assert result['status'] == 'completed'
    assert len(result['findings']) == 2
    assert [item['index'] for item in result['findings']] == [1, 2]
    request = json.loads(gateway['calls'][0].data)
    evidence = json.loads(request['messages'][1]['content'])
    assert evidence['report']['analysis_completeness']['references']
    assert 'source' not in evidence['report']['skill']
    assert evidence['skill_text_with_line_numbers'].endswith('5: Instructions.')
    assert 'DO_NOT_TRANSMIT_THIS_FILE' not in gateway['calls'][0].data.decode()
    assert result['metadata']['model'] == 'review-model'
    assert result['metadata']['response_model'] == 'served-model'
    assert result['metadata']['calls_attempted'] == result['metadata']['calls_succeeded'] == 1
    assert result['metadata']['token_usage'] is None  # Missing usage is unknown, not zero.


@pytest.mark.parametrize('provider', ['openai', 'openai_compatible', 'azure_openai'])
def test_gateway_protocol_and_usage_are_retained(skill, scanner, gateway, tmp_path, monkeypatch, provider):
    monkeypatch.setenv('SKILLSPECTOR_PROVIDER', provider)
    monkeypatch.setenv('SKILLSPECTOR_COMPAT_BASE_URL', 'https://compatible.example/api/v1')
    monkeypatch.setenv('SKILLSPECTOR_COMPAT_API_KEY', 'compat-secret')
    monkeypatch.setenv('AZURE_OPENAI_ENDPOINT', 'https://azure.example/gateway')
    monkeypatch.setenv('AZURE_OPENAI_API_KEY', 'azure-secret')
    monkeypatch.setenv('AZURE_OPENAI_DEPLOYMENT', 'review deployment')
    monkeypatch.setenv('AZURE_OPENAI_API_VERSION', '2024-10-21')
    gateway['usage'] = {'prompt_tokens': 100, 'completion_tokens': 30, 'total_tokens': 130}

    report = scan_skill(skill, tmp_path / 'reports')

    request = gateway['calls'][0]
    if provider == 'azure_openai':
        assert request.full_url == ('https://azure.example/gateway/openai/deployments/review%20deployment/'
                                    'chat/completions?api-version=2024-10-21')
        assert request.get_header('Api-key') == 'azure-secret'
        assert request.get_header('Authorization') is None
    else:
        expected = 'https://gateway.example/v1' if provider == 'openai' else 'https://compatible.example/api/v1'
        assert request.full_url == expected + '/chat/completions'
        assert request.get_header('Authorization') == ('Bearer test-secret' if provider == 'openai'
                                                       else 'Bearer compat-secret')
    result = json.loads(report.with_name('adjudication.json').read_text())
    assert result['metadata']['provider'] == provider
    assert result['metadata']['token_usage'] == gateway['usage']
    assert 'secret' not in report.with_name('adjudication.json').read_text()


@pytest.mark.parametrize('failure', ['credentials', 'model', 'unsupported', 'http', 'timeout', 'json',
                                    'missing-finding', 'contradiction', 'uncertain', 'identity', 'truncated'])
def test_adjudication_failure_is_explicit_and_preserves_native_report(
    skill, scanner, gateway, tmp_path, monkeypatch, failure,
):
    unavailable = failure in ('credentials', 'model', 'unsupported')
    if failure == 'credentials':
        monkeypatch.delenv('OPENAI_API_KEY')
        scanner['report']['metadata']['llm_available'] = False
    elif failure == 'model':
        monkeypatch.delenv('SKILLSPECTOR_MODEL')
    elif failure == 'unsupported':
        monkeypatch.setenv('SKILLSPECTOR_PROVIDER', 'anthropic')
    elif failure == 'http':
        gateway['error'] = urllib.error.HTTPError('https://gateway.example', 401, 'test-secret', {}, None)
    elif failure == 'timeout':
        gateway['error'] = TimeoutError('test-secret')
    elif failure == 'json':
        gateway['content'] = 'not JSON test-secret'
    elif failure == 'missing-finding':
        gateway['overrides'] = {'findings': []}
    elif failure == 'contradiction':
        gateway['overrides'] = {'coverage_sufficient': False}
    elif failure in ('uncertain', 'identity'):
        gateway['overrides'] = {'findings': [
            {'index': 1, 'rule_id': 'CE1' if failure == 'uncertain' else 'invented',
             'determination': 'uncertain' if failure == 'uncertain' else 'false_positive', 'reason': 'Unknown.'},
        ]}
    elif failure == 'truncated':
        gateway['finish_reason'] = 'length'
    output = tmp_path / 'reports'

    assert main(['assess', '--skill', str(skill), '--output-dir', str(output / "current")]) == 3

    raw = next(output.glob('*/skillspector.json'))
    assert json.loads(raw.read_text()) == scanner['report']
    path = raw.with_name('adjudication.json')
    result = json.loads(path.read_text())
    assert result['status'] == ('unavailable' if unavailable else 'failed')
    assert result['safe_to_use'] is None
    assert result['coverage_sufficient'] is None
    assert result['findings'][0]['determination'] == 'not_adjudicated'
    assert result['metadata']['calls_attempted'] == (0 if unavailable else 1)
    assert len(gateway['calls']) == (0 if unavailable else 1)  # No retry or provider fallback.
    assert 'test-secret' not in path.read_text()
    if failure == 'truncated':
        assert 'output token limit' in result['summary']
    elif failure == 'timeout':
        assert 'timed out' in result['summary']


def test_true_positive_is_advice_not_execution_failure(skill, scanner, gateway, tmp_path):
    gateway['overrides'] = {
        'safe_to_use': False,
        'findings': [{'index': 1, 'rule_id': 'CE1', 'determination': 'true_positive', 'reason': 'Unsafe eval.'}],
    }
    output = tmp_path / 'reports'

    assert main(['assess', '--skill', str(skill), '--output-dir', str(output / "current")]) == 0

    result = json.loads(next(output.glob('*/adjudication.json')).read_text())
    assert result['safe_to_use'] is False
    assert result['status'] == 'completed'


@pytest.mark.parametrize('scenario', ['findings', 'no-findings', 'partial', 'failed', 'missing'])
def test_static_only_records_unadjudicated_findings_without_inference(skill, scanner, gateway, tmp_path, scenario):
    scanner['report']['metadata'] = {'llm_requested': False}
    scanner['report']['issues'] = [
        {'id': 'AR3', 'severity': 'HIGH', 'location': {'file': 'SKILL.md', 'start_line': 278}},
        {'id': 'AS3', 'severity': 'MEDIUM', 'location': {'file': 'SKILL.md', 'start_line': 9}},
    ]
    if scenario == 'no-findings':
        scanner['report']['issues'] = []
    elif scenario == 'partial':
        scanner['report']['analysis_completeness']['is_complete'] = False
    elif scenario == 'failed':
        scanner['report']['execution_successful'] = False
    elif scenario == 'missing':
        scanner['report'] = None
    output = tmp_path / 'reports'

    code = main(['assess', '--skill', str(skill), '--scan-mode', 'static-only',
                 '--output-dir', str(output / "current")])

    assert code == (3 if scenario in ('failed', 'missing') else 0)
    assert not gateway['calls']
    assert '--no-llm' in scanner['calls'][0]
    run = next(output.iterdir())
    if scanner['report'] is None:
        assert not (run / 'skillspector.json').exists()
        issues = []
    else:
        assert json.loads((run / 'skillspector.json').read_text()) == scanner['report']
        issues = scanner['report']['issues']
    result = json.loads((run / 'adjudication.json').read_text())
    assert set(result) == ({'skill_sha256'} if code == 0 else set()) | {
        'safe_to_use', 'summary', 'coverage_sufficient', 'coverage_reason', 'findings', 'status', 'scope', 'metadata',
    }
    assert result['status'] == 'not_performed'
    assert result['safe_to_use'] is None
    assert result['coverage_sufficient'] is None
    assert result['summary']
    assert result['coverage_reason']
    assert result['scope']
    assert [(f['index'], f['rule_id'], f['determination']) for f in result['findings']] == [
        (index, issue['id'], 'not_adjudicated') for index, issue in enumerate(issues, 1)
    ]
    assert all(f['reason'] for f in result['findings'])
    metadata = result['metadata']
    assert metadata.pop('created_at')
    assert metadata == {
        'provider': None, 'model': None, 'response_model': None, 'duration_seconds': 0.0,
        'calls_attempted': 0, 'calls_succeeded': 0, 'token_usage': None,
    }


@pytest.mark.parametrize('static_only', [False, True])
def test_adjudication_storage_failure_preserves_native_report(skill, scanner, tmp_path, monkeypatch, static_only):
    scanner['report']['metadata']['llm_requested'] = not static_only
    original_open = Path.open

    def open_file(path, *args, **kwargs):
        if path.name == 'adjudication.json':
            raise PermissionError('storage unavailable')
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', open_file)
    output = tmp_path / 'reports'
    options = ['--scan-mode', 'static-only'] if static_only else []

    assert main(['assess', '--skill', str(skill), '--output-dir', str(output / "current"), *options]) == 1

    assert json.loads(next(output.glob('*/skillspector.json')).read_text()) == scanner['report']


@pytest.mark.parametrize('version', ['2.10.0', '2.11.1', '3.0.0', 'unknown'])
def test_unsupported_scanner_does_not_create_reports(skill, scanner, tmp_path, version):
    scanner['version'] = f'SkillSpector v{version}'
    output = tmp_path / 'reports'
    assert main(['assess', '--skill', str(skill), '--output-dir', str(output)]) == 3
    assert not scanner['calls']
    assert not output.exists()


@pytest.mark.parametrize('override', [False, True])
def test_execution_settings_reach_scanner_and_adjudicator(skill, scanner, gateway, tmp_path, monkeypatch, override):
    monkeypatch.delenv('SKILLSPECTOR_MAX_WORKFLOW_SECONDS', raising=False)
    monkeypatch.setenv('SKILLSPECTOR_REASONING_EFFORT', 'medium')
    args = ['assess', '--skill', str(skill), '--output-dir', str(tmp_path / 'reports')]
    if override:
        args += ['--timeout', '120', '--max-completion-tokens', '65536']
        monkeypatch.setenv('SKILLSPECTOR_MAX_WORKFLOW_SECONDS', '100')
    assert main(args) == 0
    assert scanner['timeouts'] == [120 if override else 600]
    assert float(scanner['environment']['SKILLSPECTOR_MAX_WORKFLOW_SECONDS']) == (100 if override else 540)
    payload = json.loads(gateway['calls'][0].data)
    assert payload['max_completion_tokens'] == (65536 if override else 32768)
    assert payload['reasoning_effort'] == 'medium'


@pytest.mark.parametrize(('timeout', 'override', 'configured'), [
    (600, None, '540'), (1200, None, '1080'), (600, '300', '300'),
])
def test_workflow_deadline_guidance_uses_configured_limit_and_preserves_reports(
    skill, scanner, tmp_path, monkeypatch, capsys, timeout, override, configured,
):
    monkeypatch.delenv('SKILLSPECTOR_MAX_WORKFLOW_SECONDS', raising=False)
    if override is not None:
        monkeypatch.setenv('SKILLSPECTOR_MAX_WORKFLOW_SECONDS', override)
    output = tmp_path / 'reports'
    args = ['assess', '--skill', str(skill), '--output-dir', str(output), '--timeout', str(timeout)]
    assert main(args) == 0
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    scanner['report']['metadata']['llm_degraded'] = True
    scanner['report']['analysis_completeness']['ledger_exceptions'] = [{'reason_code': 'runtime_limit'}]
    capsys.readouterr()

    assert main(args) == 3

    error = capsys.readouterr().err
    assert f'workflow limit: {configured} seconds' in error
    assert f'--timeout {timeout * 2}' in error
    assert 'SKILLSPECTOR_MAX_WORKFLOW_SECONDS' in error
    assert scanner['environment']['SKILLSPECTOR_MAX_WORKFLOW_SECONDS'] == configured
    assert {p.name: p.read_bytes() for p in output.iterdir()} == before
    assert str(next(tmp_path.glob('my-skill-*'))) in error


def test_timeout_option_name_drives_parsing_and_deadline_guidance(skill, scanner, tmp_path, monkeypatch, capsys):
    from skill_assessment.commands import assess as command

    monkeypatch.setattr(command, 'TIMEOUT_FLAG', '--request-timeout')
    monkeypatch.delenv('SKILLSPECTOR_MAX_WORKFLOW_SECONDS', raising=False)
    scanner['report']['metadata']['llm_degraded'] = True
    scanner['report']['analysis_completeness']['ledger_exceptions'] = [{'reason_code': 'runtime_limit'}]
    assert main(['assess', '--skill', str(skill), '--output-dir', str(tmp_path / 'reports'),
                 '--request-timeout', '900']) == 3
    assert scanner['timeouts'] == [900]
    assert '--request-timeout 1800' in capsys.readouterr().err
