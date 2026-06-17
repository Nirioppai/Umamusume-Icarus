import json
from pathlib import Path

from fastapi.testclient import TestClient

from career_bot import event_outcomes, local_llm
from career_bot.events import EventManager


def test_normalize_dumper_outcomes_and_score_by_event_name(tmp_path, monkeypatch):
    monkeypatch.setenv('UMA_RUNTIME_DIR', str(tmp_path / 'uma_runtime'))
    (tmp_path / 'data').mkdir()
    payload = {
        'Dance Lesson': {
            '0': {'1': {'speed': 10}},
            '1': {'2': {'vital': 20, 'skill_point': 5}},
        }
    }
    normalized = event_outcomes.normalize_dumper_outcomes(payload)
    assert normalized
    (tmp_path / 'data' / 'event_outcomes.json').write_text(json.dumps(normalized), encoding='utf-8')
    mgr = EventManager(tmp_path)
    event = {
        'story_id': 'unknown-story-id',
        'title': 'Dance Lesson',
        'event_contents_info': {'choice_array': [{'select_index': 1}, {'select_index': 2}]},
    }
    assert mgr.choose(event, {'prioritize_event_energy': True}, 12, {'vital': 40, 'max_vital': 100, 'motivation': 4}) == 1
    assert mgr.last_choice_trace['reason'] == 'weighted_outcome'
    assert 'vital' in mgr.last_choice_trace['scores'][1]['reason']


def test_import_bundled_outcomes_writes_kb_and_dataset_rows(tmp_path, monkeypatch):
    monkeypatch.setenv('UMA_RUNTIME_DIR', str(tmp_path / 'uma_runtime'))
    (tmp_path / 'data').mkdir()
    (tmp_path / 'data' / 'event_outcomes.json').write_text('{}', encoding='utf-8')
    (tmp_path / 'data' / event_outcomes.BUNDLED_IMPORT).write_text(json.dumps({
        'Mystery Fortune Ritual!': {'0': {'1': {'speed': 7, 'stamina': 7}, '2': {'wiz': 4}}}
    }), encoding='utf-8')
    report = event_outcomes.import_outcomes(tmp_path)
    assert report['success'] is True
    assert report['imported_events'] == 1
    summary = event_outcomes.summary(tmp_path)
    assert summary['known_events'] == 1
    assert summary['known_choices'] == 2
    rows = (tmp_path / 'uma_runtime' / 'ai' / event_outcomes.DATASET_FILE).read_text(encoding='utf-8').strip().splitlines()
    assert len(rows) == 2


def test_local_llm_prompt_includes_event_outcome_context(tmp_path, monkeypatch):
    monkeypatch.setenv('UMA_RUNTIME_DIR', str(tmp_path / 'uma_runtime'))
    ai = tmp_path / 'uma_runtime' / 'ai'
    ai.mkdir(parents=True, exist_ok=True)
    (ai / 'turn_decisions.jsonl').write_text(json.dumps({
        'run_id': 'run1',
        'scenario_id': 1,
        'turn': 1,
        'state': {'speed': 100, 'stamina': 100, 'power': 100, 'guts': 100, 'wit': 100, 'skill_point': 0, 'hp': 50, 'mood': 4, 'fans': 0},
        'action': {'type': 'event', 'reason': 'sample'},
        'outcome': {'reward': 1},
    }) + '\n', encoding='utf-8')
    (ai / 'career_summaries.jsonl').write_text(json.dumps({'run_id': 'run1', 'status': 'completed'}) + '\n', encoding='utf-8')
    (tmp_path / 'data').mkdir()
    (tmp_path / 'data' / 'event_outcomes.json').write_text(json.dumps(
        event_outcomes.normalize_dumper_outcomes({'Dance Lesson': {'0': {'1': {'speed': 10}}}})
    ), encoding='utf-8')
    local_llm.save_config(tmp_path, {'enabled': True, 'mode': 'offline', 'model': 'test', 'base_url': 'http://localhost:1234/v1'})
    seen_packets = []

    class Resp:
        status_code = 200
        def raise_for_status(self): return None
        def json(self): return {'choices': [{'message': {'content': '{"summary":"ok"}'}}]}

    def fake_post(url, headers=None, json=None, timeout=None):
        seen_packets.append(json['messages'][1]['content'])
        return Resp()

    result = local_llm.analyze_latest_run(tmp_path, post_fn=fake_post)
    assert result['success'] is True
    assert 'event_outcome_knowledge' in seen_packets[0]
    assert 'Dance Lesson' in seen_packets[0]
