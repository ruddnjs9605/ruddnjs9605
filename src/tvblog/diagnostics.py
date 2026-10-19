"""Read-only network diagnostics; never dump proxy values or verbose curl output."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

from requests.utils import get_environ_proxies

from .models import now

DIAGNOSTIC_HOSTS = ("example.com", "github.com", "program.kbs.co.kr", "iaudience.kbs.co.kr")
ALL_KBS_HOSTS = ("program.kbs.co.kr", "www.kbs.co.kr", "schedule.kbs.co.kr",
                 "pbbs.kbs.co.kr", "apis.kbs.co.kr", "iaudience.kbs.co.kr")
ALL_DIAGNOSTIC_HOSTS = ("example.com", "github.com", *ALL_KBS_HOSTS)
PROXY_NAMES = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
               "http_proxy", "https_proxy", "all_proxy", "no_proxy")


def classify_curl(returncode: int, output: str) -> dict:
    # Whitelist numeric write-out only. stderr may contain credentials; never persist it.
    match = re.search(r"TVBLOG_METRICS (\d{3}) (\d{3}) (\d+)\s*$", output)
    if not match:
        return {"curl_exit_code": returncode, "connect": "unknown", "tls": "unknown",
                "origin_http": "unknown", "failure_stage": "diagnostic_unavailable"}
    connect, http, verify = map(int, match.groups())
    result = {"curl_exit_code": returncode, "connect_http_status": connect or None,
              "origin_http_status": http or None, "tls": "not_reached",
              "connect": "not_observed", "origin_http": "not_reached", "failure_stage": None}
    if connect:
        result["connect"] = "established" if connect == 200 else "rejected"
        if connect != 200:
            result["failure_stage"] = "connect_proxy"
            return result
    if http:
        result.update(tls="verified" if verify == 0 else "verification_failed",
                      origin_http="response_received", tls_verify_code=verify)
        if http >= 400:
            result["failure_stage"] = "origin_http"
    elif returncode in (35, 51, 58, 60, 77, 83, 90, 91):
        result.update(tls="failed", tls_verify_code=verify, failure_stage="tls")
    elif returncode == 5:
        result["failure_stage"] = "proxy_dns"
    elif returncode == 6:
        result["failure_stage"] = "curl_dns"
    elif returncode == 7:
        result["failure_stage"] = "tcp_connection"
    elif returncode == 28:
        result["failure_stage"] = "timeout_stage_unknown"
    elif returncode:
        result["failure_stage"] = "transport_stage_unknown"
    return result


def dns_status(host: str) -> dict:
    # Bound OS resolver time using a subprocess; addresses are intentionally omitted.
    code = "import socket,sys; socket.getaddrinfo(sys.argv[1],443,type=socket.SOCK_STREAM)"
    try:
        r = subprocess.run([sys.executable, "-c", code, host], capture_output=True, timeout=6)
        return {"status": "resolved" if r.returncode == 0 else "failed",
                "scope": "container_local_resolver_not_proxy_resolver"}
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "scope": "container_local_resolver_not_proxy_resolver"}


def diagnose(hosts=DIAGNOSTIC_HOSTS) -> dict:
    report = {"mode": "network_diagnostics", "started_at": now(),
              "proxy_variable_presence": {name: bool(os.environ.get(name)) for name in PROXY_NAMES},
              "environment_generation": "unknown_no_live_instance_status_tool",
              "notes": ["Environment variable values, proxy URLs, credentials and raw curl stderr are not stored",
                        "DNS is a separate observation; CONNECT proxies may resolve destination hosts themselves",
                        "No proxy disabling, direct fallback, insecure TLS or redirect following is used",
                        "HEAD requests only; no broadcast content is collected"], "hosts": []}
    for host in hosts:
        url = f"https://{host}/"
        proxies = get_environ_proxies(url)
        entry = {"host": host, "local_dns": dns_status(host),
                 "environment_proxy_selected": bool(proxies.get("https") or proxies.get("all"))}
        try:
            r = subprocess.run(["curl", "--head", "--silent", "--show-error", "--no-insecure", "--no-location", "--max-time", "12",
                                "--output", os.devnull, "--write-out",
                                "TVBLOG_METRICS %{http_connect} %{http_code} %{ssl_verify_result}\n", url],
                               capture_output=True, text=True, timeout=15)
            entry.update(classify_curl(r.returncode, r.stdout))
        except FileNotFoundError:
            entry.update(failure_stage="diagnostic_unavailable", detail="curl_not_installed")
        except subprocess.TimeoutExpired:
            entry.update(failure_stage="diagnostic_timeout")
        report["hosts"].append(entry)
    report["finished_at"] = now()
    return report
