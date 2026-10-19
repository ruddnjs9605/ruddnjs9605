"""Transport-stage classifications use synthetic curl output; no live requests."""
import json
from types import SimpleNamespace

import pytest

from tvblog import diagnostics


@pytest.mark.parametrize("code,metrics,stage,tls", [
    (56, "403 000 0", "connect_proxy", "not_reached"),
    (56, "407 000 0", "connect_proxy", "not_reached"),
    (0, "200 200 0", None, "verified"),
    (0, "200 403 0", "origin_http", "verified"),
    (60, "200 000 20", "tls", "failed"),
    (6, "000 000 0", "curl_dns", "not_reached"),
    (5, "000 000 0", "proxy_dns", "not_reached"),
    (28, "200 000 0", "timeout_stage_unknown", "not_reached"),
])
def test_transport_stages(code, metrics, stage, tls):
    r = diagnostics.classify_curl(code, "TVBLOG_METRICS " + metrics + "\n")
    assert r["failure_stage"] == stage
    assert r["tls"] == tls
    if stage == "connect_proxy":
        assert r["origin_http_status"] is None


def test_no_raw_proxy_credentials_or_stderr_saved(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://user:SUPERSECRET@proxy.invalid:8080")
    monkeypatch.setattr(diagnostics, "dns_status", lambda _: {"status": "failed"})
    monkeypatch.setattr(diagnostics, "get_environ_proxies", lambda _: {"https": "SECRET"})
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=56, stdout="TVBLOG_METRICS 403 000 0\n", stderr="SUPERSECRET proxy details")
    monkeypatch.setattr(diagnostics.subprocess, "run", run)
    result = diagnostics.diagnose()
    serialized = json.dumps(result)
    assert result["proxy_variable_presence"]["HTTPS_PROXY"] is True
    assert "SUPERSECRET" not in serialized and "proxy.invalid" not in serialized
    assert "user:" not in serialized
    assert all("--insecure" not in command and "--noproxy" not in command for command in calls)
    assert result["environment_generation"].startswith("unknown")


def test_missing_metrics_are_unknown_not_false_success():
    r = diagnostics.classify_curl(0, "not curl metrics")
    assert r["failure_stage"] == "diagnostic_unavailable"
    assert r["tls"] == "unknown"


def test_diagnose_cli_saves_safe_report_and_preserves_failure_exit(tmp_path, monkeypatch):
    import tvblog.cli as cli
    monkeypatch.setattr(cli, "diagnose", lambda: {"mode": "network_diagnostics", "hosts": [{"failure_stage": "connect_proxy"}]})
    out = tmp_path / "diagnose"
    assert cli.main(["diagnose", "--out", str(out)]) == 2
    assert json.loads((out / "report.json").read_text())["hosts"][0]["failure_stage"] == "connect_proxy"
    assert json.loads((out / "records.json").read_text()) == []


def test_all_kbs_cli_passes_exact_host_set(tmp_path, monkeypatch):
    import tvblog.cli as cli
    from tvblog.diagnostics import ALL_DIAGNOSTIC_HOSTS
    called = []
    def diagnose(hosts):
        called.extend(hosts)
        return {"mode": "network_diagnostics", "hosts": []}
    monkeypatch.setattr(cli, "diagnose", diagnose)
    assert cli.main(["diagnose", "--all-kbs", "--out", str(tmp_path / "all")]) == 0
    assert called == list(ALL_DIAGNOSTIC_HOSTS) and len(called) == 8
