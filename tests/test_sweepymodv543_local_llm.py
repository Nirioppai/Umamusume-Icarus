import json
from pathlib import Path

from career_bot import local_llm
from career_bot.ai_dataset import _append_jsonl, DATASET_FILES


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
    def raise_for_status(self):
        return None
    def json(self):
        return self.payload


def fake_post(url, headers=None, json=None, timeout=None):
    assert url.endswith('/chat/completions')
    assert json['messages']
    content = {
        'summary': 'The run was stable but energy planning could improve.',
        'risk_flags': ['low energy before races'],
        'candidate_rules': [{'rule': 'Prefer rest when HP is low and training value is weak.', 'confidence': 0.7}],
        'recommendation': 'Keep Sweepy decision as baseline.',
    }
    return FakeResponse({'choices': [{'message': {'content': json_module.dumps(content)}}]})


# Keep a module alias so the fake argument named json does not hide json.dumps.
json_module = json


def write_sample_dataset(root: Path):
    ai = root / 'uma_runtime' / 'ai'
    ai.mkdir(parents=True, exist_ok=True)
    rows = []
    for turn in range(1, 4):
        rows.append({
            'dataset': 'turn_decisions',
            'run_id': 'run_a',
            'scenario_id': 4,
            'turn': turn,
            'state': {'speed': 100 + turn, 'stamina': 80, 'power': 90, 'guts': 70, 'wit': 60, 'skill_point': 10, 'hp': 50, 'mood': 3, 'fans': 1000},
            'action': {'type': 'train', 'reason': 'sample', 'command_type': 1, 'command_id': turn},
            'outcome': {'reward': 1.5 * turn},
            'candidate_context': {'training_candidates': [{'score': turn}]},
            'turn_metadata': {'api_context': {'available_race_program_ids': []}},
        })
    _append_jsonl(ai / DATASET_FILES['turn_decisions'], rows)
    _append_jsonl(ai / DATASET_FILES['career_summaries'], [{
        'dataset': 'career_summaries',
        'run_id': 'run_a',
        'scenario_id': 4,
        'status': 'completed',
        'final_fans': 12345,
        'final_stats': {'speed': 500},
    }])


def test_local_llm_config_normalizes_and_redacts(tmp_path, monkeypatch):
    monkeypatch.setenv('UMA_RUNTIME_DIR', str(tmp_path / 'uma_runtime'))
    cfg = local_llm.save_config(tmp_path, {
        'enabled': True,
        'provider': 'OLLAMA',
        'base_url': 'http://localhost:11434/v1/',
        'model': 'qwen3:8b',
        'api_key': 'secret-token',
        'mode': 'shadow',
        'allow_live_override': True,
    })
    assert cfg['provider'] == 'ollama'
    assert cfg['base_url'] == 'http://localhost:11434/v1'
    assert cfg['allow_live_override'] is False
    latest = local_llm.latest_payload(tmp_path)
    assert latest['config']['api_key'].endswith('oken')
    assert latest['config']['api_key_set'] is True


def test_local_llm_test_connection_and_analysis(tmp_path, monkeypatch):
    monkeypatch.setenv('UMA_RUNTIME_DIR', str(tmp_path / 'uma_runtime'))
    write_sample_dataset(tmp_path)
    local_llm.save_config(tmp_path, {'enabled': True, 'mode': 'shadow', 'base_url': 'http://localhost:1234/v1', 'model': 'test-model'})
    test = local_llm.test_connection(tmp_path, post_fn=fake_post)
    assert test['success'] is True
    analysis = local_llm.analyze_latest_run(tmp_path, post_fn=fake_post)
    assert analysis['success'] is True
    assert analysis['analysis']['summary'].startswith('The run was stable')
    shadow = local_llm.shadow_advice(tmp_path, post_fn=fake_post)
    assert shadow['success'] is True
    dash = local_llm.dashboard_summary(tmp_path)
    assert dash['enabled'] is True
    assert dash['last_connection_success'] is True
    assert dash['summary_headline']


def test_local_llm_blank_api_key_preserves_saved_secret(tmp_path, monkeypatch):
    monkeypatch.setenv('UMA_RUNTIME_DIR', str(tmp_path / 'uma_runtime'))
    first = local_llm.save_config(tmp_path, {
        'enabled': True,
        'provider': 'custom',
        'base_url': 'http://localhost:9999/v1',
        'model': 'first-model',
        'api_key': 'keep-me',
        'mode': 'offline',
    })
    assert first['api_key'] == 'keep-me'
    second = local_llm.save_config(tmp_path, {
        'enabled': True,
        'model': 'second-model',
        'api_key': '',
    })
    assert second['model'] == 'second-model'
    assert second['api_key'] == 'keep-me'
    latest = local_llm.latest_payload(tmp_path)
    assert latest['config']['api_key_set'] is True


def test_local_llm_analysis_prompt_is_budgeted_for_large_runs(tmp_path, monkeypatch):
    monkeypatch.setenv('UMA_RUNTIME_DIR', str(tmp_path / 'uma_runtime'))
    ai = tmp_path / 'uma_runtime' / 'ai'
    ai.mkdir(parents=True, exist_ok=True)
    rows = []
    long_reason = 'support stack / scenario planning detail ' * 80
    for turn in range(1, 121):
        rows.append({
            'dataset': 'turn_decisions',
            'run_id': 'run_large',
            'scenario_id': 4,
            'turn': turn,
            'state': {'speed': 100 + turn, 'stamina': 80, 'power': 90, 'guts': 70, 'wit': 60, 'skill_point': 10, 'hp': 50, 'mood': 3, 'fans': 1000},
            'action': {'type': 'train', 'reason': long_reason, 'command_type': 1, 'command_id': turn},
            'outcome': {'reward': 1.5 * turn},
            'candidate_context': {'training_candidates': [{'score': turn}] * 10},
            'turn_metadata': {'api_context': {'available_race_program_ids': list(range(50))}},
        })
    _append_jsonl(ai / DATASET_FILES['turn_decisions'], rows)
    _append_jsonl(ai / DATASET_FILES['career_summaries'], [{'dataset': 'career_summaries', 'run_id': 'run_large', 'scenario_id': 4, 'status': 'completed'}])
    local_llm.save_config(tmp_path, {'enabled': True, 'mode': 'offline', 'base_url': 'http://localhost:1234/v1', 'model': 'test-model', 'max_turns_per_prompt': 120})

    def budget_asserting_post(url, headers=None, json=None, timeout=None):
        packet = json['messages'][1]['content']
        assert len(packet) <= local_llm.PROMPT_CHAR_BUDGET + 500
        content = {'summary': 'Large run analyzed from a budgeted prompt.'}
        return FakeResponse({'choices': [{'message': {'content': json_module.dumps(content)}}]})

    analysis = local_llm.analyze_latest_run(tmp_path, post_fn=budget_asserting_post)
    assert analysis['success'] is True
    assert analysis['turns_sent'] <= 120
    assert analysis['analysis']['summary'].startswith('Large run')


def test_local_llm_parser_unwraps_analysis_envelope_and_raw_text():
    wrapped = json_module.dumps({
        'analysis': {
            'key_patterns': [{'pattern': 'Training Cycle Focus', 'description': 'Balanced speed and wit.'}],
            'repeatable_rules': [{'rule': 'Prefer wit before high-value races.'}],
        }
    })
    parsed = local_llm.normalize_analysis_payload(wrapped)
    assert 'analysis' not in parsed
    assert parsed['key_patterns'][0]['pattern'] == 'Training Cycle Focus'
    assert parsed['repeatable_rules'][0]['rule'].startswith('Prefer wit')

    raw_wrapped = {'raw_text': wrapped}
    parsed2 = local_llm._unwrap_model_payload(raw_wrapped, preferred_key='analysis')
    assert parsed2['key_patterns'][0]['pattern'] == 'Training Cycle Focus'


def test_local_llm_analysis_saves_structured_payload_from_enveloped_model(tmp_path, monkeypatch):
    monkeypatch.setenv('UMA_RUNTIME_DIR', str(tmp_path / 'uma_runtime'))
    write_sample_dataset(tmp_path)
    local_llm.save_config(tmp_path, {'enabled': True, 'mode': 'offline', 'base_url': 'http://localhost:1234/v1', 'model': 'test-model'})

    def enveloped_post(url, headers=None, json=None, timeout=None):
        content = {
            'analysis': {
                'key_patterns': [{'pattern': 'Post-Loss Recovery', 'description': 'Rest after large loss.'}],
                'risks': ['Delayed recovery can miss races'],
                'repeatable_rules': [{'rule': 'Rest after major HP loss.', 'condition': 'HP low'}],
            }
        }
        return FakeResponse({'choices': [{'message': {'content': json_module.dumps(content)}}]})

    result = local_llm.analyze_latest_run(tmp_path, post_fn=enveloped_post, force=True)
    assert result['success'] is True
    assert result['analysis']['key_patterns'][0]['pattern'] == 'Post-Loss Recovery'
    assert result['analysis']['repeatable_rules'][0]['rule'].startswith('Rest')
    assert result['raw_text'] == ''
