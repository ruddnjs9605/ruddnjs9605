"""Synthetic input tests; no actual KBS dataset is represented here."""
import json
from copy import deepcopy
from pathlib import Path

from tvblog.candidates import generate_candidates
from tvblog.cli import main
from tvblog.models import fact
from tvblog.parser import parse_detail

FIXTURE = Path(__file__).parent / 'fixtures/synthetic/special.html'
URL = 'https://iaudience.kbs.co.kr/__synthetic_fixture__/special'


def rows():
    return parse_detail(FIXTURE.read_text(), URL, 'synthetic_fixture')[0]


def test_unreviewed_facts_stay_separate_and_metrics_unknown():
    data = rows()
    result = generate_candidates(data)
    assert len(result) == 2
    c = result[0]
    assert '가상식당 감마' in c['recommended_title']
    assert c['confirmed_facts'] == {}
    assert 'name' in c['unreviewed_extractions']
    assert c['search_volume'] == c['popularity'] == '확인 필요'
    assert c['keyword_status'] == '예상 검색 키워드'
    assert c['title_status'] == 'needs_review'
    assert c['draft_generation_possible'] is False
    assert 'price' in c['unknown_information'] and 'opening_hours' in c['unknown_information']
    assert all(c['publication_ready'] is False for c in result)


def test_schedule_is_not_substituted_for_original_date():
    c = generate_candidates(rows())[0]
    assert c['broadcast_date']['value'] == '2026-09-01'
    assert c['scheduled_date']['value'] == '확인 필요'
    assert '2026-10-18' not in c['broadcast_date']['value']


def test_only_explicit_approval_allows_non_synthetic_draft():
    data = rows()
    for f in data[0]['facts'].values():
        if f['status'] == 'extracted_needs_review':
            f['status'] = 'human_verified'
    assert generate_candidates(data)[0]['draft_generation_possible'] is False
    # This is a test of the readiness gate only, not a real dataset.
    data[0]['source_mode'] = 'provided_html'
    c = generate_candidates(data)[0]
    assert c['draft_generation_possible'] is True
    assert c['title_status'] == 'human_verified_inputs'
    assert c['publication_ready'] is False


def test_no_name_no_evidence_and_duplicates_are_not_candidates():
    data = rows()
    no_name = deepcopy(data[0]); no_name['facts']['name'] = fact()
    assert not generate_candidates([no_name])
    no_evidence = deepcopy(data[0]); no_evidence['facts']['name']['evidence'] = ''
    assert not generate_candidates([no_evidence])
    assert len(generate_candidates([data[0], data[0]])) == 1
    wrong_source = deepcopy(data[0]); wrong_source['official_source_url'] = 'https://example.org/'
    assert not generate_candidates([wrong_source])


def test_candidate_command_and_empty_case(tmp_path):
    p = tmp_path / 'records.json'; p.write_text(json.dumps(rows()))
    out = tmp_path / 'candidates'
    assert main(['candidates', '--records', str(p), '--out', str(out)]) == 0
    result = json.loads((out / 'candidates.json').read_text())
    assert len(result) == 2 and all(c['synthetic'] for c in result)
    assert (out / 'candidates.csv').exists()
    assert main(['candidates', '--records', str(p), '--out', str(out)]) == 1
    p.write_text('[]')
    assert main(['candidates', '--records', str(p), '--out', str(tmp_path / 'empty')]) == 2
