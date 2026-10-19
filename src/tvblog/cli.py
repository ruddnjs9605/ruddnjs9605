from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .candidates import export_candidates, generate_candidates
from .collector import collect, probe
from .diagnostics import ALL_DIAGNOSTIC_HOSTS, diagnose
from .export import export_run
from .http import Client
from .models import now
from .importing import import_manifest
from .review import apply_review


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def output_dir(value):
    return Path(value) if value else Path("outputs") / datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d-%H%M%S-%f")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="생생정보 출처 기반 수집 및 검토용 초안. 자동 게시는 지원하지 않습니다.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("probe", "collect", "import-html", "review", "diagnose"):
        command = sub.add_parser(name)
        command.add_argument("--out", help="새 출력 디렉터리 (기존 디렉터리 덮어쓰기 금지)")
        if name == "diagnose":
            command.add_argument("--all-kbs", action="store_true", help="일반 2개와 KBS 6개 호스트를 한 번씩 진단")
        elif name == "collect":
            command.add_argument("--listing-url", help="공식 페이지에서 확인한 방송정보 목록 HTTPS URL")
            command.add_argument("--count", type=int, choices=range(1, 6), default=5)
        elif name == "import-html":
            command.add_argument("--manifest", required=True)
            command.add_argument("--fixture", action="store_true", help="합성 테스트 자료임을 결과에 표시")
        elif name == "review":
            command.add_argument("--records", required=True)
            command.add_argument("--decisions", required=True)
    candidate_command = sub.add_parser("candidates", help="근거가 있는 추출값에서 검토용 제목 후보 생성")
    candidate_command.add_argument("--records", required=True)
    candidate_command.add_argument("--out", help="새 출력 디렉터리")
    template = sub.add_parser("review-template")
    template.add_argument("--records", required=True)
    template.add_argument("--out", required=True, help="새 JSON 파일 경로")
    args = parser.parse_args(argv)
    try:
        if args.command == "review-template":
            records = read_json(args.records)
            template = {"reviewer": "", "records": [
                {"id": item["id"], "fields": {
                    key: {"expected_value": f["value"], "evidence": f["evidence"], "note": ""}
                    for key, f in item["facts"].items() if f["status"] == "extracted_needs_review"},
                 "additional_sources": []} for item in records]}
            # Exclusive creation preserves earlier human review work.
            with Path(args.out).open("x", encoding="utf-8") as stream:
                json.dump(template, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            return 0
        out = output_dir(args.out)
        if out.exists():
            raise ValueError("출력 디렉터리가 이미 존재합니다: 기존 결과 보존을 위해 새 --out 경로를 사용하세요")
        if args.command == "candidates":
            candidates = generate_candidates(read_json(args.records))
            report = {"mode": "rule_based_candidates", "status": "generated" if candidates else "no_eligible_records",
                      "candidate_count": len(candidates), "finished_at": now(), "publication_ready": False}
            export_candidates(out, report, candidates)
            print(json.dumps({"status": report["status"], "candidate_count": len(candidates), "output": str(out)}, ensure_ascii=False))
            return 0 if candidates else 2
        if args.command == "diagnose":
            report, records = (diagnose(hosts=ALL_DIAGNOSTIC_HOSTS) if args.all_kbs else diagnose()), []
            report["status"] = "network_checked"
            exit_code = 2 if any(e.get("failure_stage") for e in report["hosts"]) else 0
        elif args.command == "probe":
            report, records = probe(Client()), []
            exit_code = 0 if any(e["outcome"] == "html_accessible" for e in report["events"]) else 2
        elif args.command == "collect":
            report, records = collect(Client(), args.listing_url, args.count)
            exit_code = 0 if report["status"] == "collected_needs_review" else 2
        elif args.command == "import-html":
            report, records = import_manifest(Path(args.manifest), args.fixture)
            exit_code = 0 if report["status"] == "imported_needs_review" else 2
        else:
            records = apply_review(read_json(args.records), read_json(args.decisions))
            report = {"mode": "human_review", "status": "review_applied", "record_count": len(records),
                      "finished_at": now(), "publication_ready": False}
            exit_code = 0
        export_run(out, report, records)
        print(json.dumps({"status": report["status"], "record_count": len(records), "output": str(out)}, ensure_ascii=False))
        return exit_code
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
