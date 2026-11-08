"""Offline contract and failure tests; these never call Azure."""
import json
from dataclasses import replace
from types import SimpleNamespace
import httpx
from openai import OpenAI
from pydantic import SecretStr
import pytest
from docflow.config import AzureSettings
from docflow.inference import InferenceSession, ProviderError, narrative_lines, validate_interpretation
from docflow.jobs import process_batch, JobStore
from docflow.models import Batch
from docflow.safety import Budget
from docflow.workload import narrative_text, text_document


def settings():
    return AzureSettings('https://example.openai.azure.com/openai/v1/', 'gpt-5-mini', SecretStr('offline-secret'))


def output(text):
    selected = narrative_lines(text)
    names = next((n, line) for n, line in selected if 'supplying' in line or 'supplied' in line)
    date = next((n, line) for n, line in selected if 'issued' in line)
    return json.dumps({'fields': [
        {'name': 'supplier', 'value': 'Cedar Systems', 'source_line': names[0], 'quote': names[1]},
        {'name': 'date', 'value': '2026-10-15', 'source_line': date[0], 'quote': date[1]}]})


def response_body(text):
    return {'id': 'resp_offline', 'object': 'response', 'created_at': 1, 'status': 'completed',
        'model': 'gpt-5-mini', 'output': [{'id': 'msg_offline', 'type': 'message', 'role': 'assistant',
            'status': 'completed', 'content': [{'type': 'output_text', 'text': output(text), 'annotations': []}]}],
        'usage': {'input_tokens': 100, 'output_tokens': 80, 'total_tokens': 180,
            'input_tokens_details': {'cached_tokens': 0}, 'output_tokens_details': {'reasoning_tokens': 0}}}


def test_identity_covers_content_job_and_model_contract(monkeypatch):
    import docflow.inference as module
    session = InferenceSession('a'); session.settings = settings()
    text = narrative_text()
    original = session.identity(text, 'invoice')
    assert original != session.identity(text + '\nChanged', 'invoice')
    assert original != session.identity(text, 'purchase_order')
    session.job_id = 'b'; assert original != session.identity(text, 'invoice')
    session.job_id = 'a'
    for field, value in [('deployment', 'other'), ('base_url', 'https://other.openai.azure.com/openai/v1/'),
                         ('reasoning_effort', 'low'), ('max_output_tokens', 512)]:
        session.settings = replace(settings(), **{field: value})
        assert original != session.identity(text, 'invoice')
    session.settings = settings()
    monkeypatch.setattr(module, 'PROMPT_VERSION', 'changed')
    assert original != session.identity(text, 'invoice')


@pytest.mark.parametrize('damage', ['source', 'quote', 'duplicate', 'name', 'missing'])
def test_invalid_output_is_rejected(damage):
    text = narrative_text(); value = json.loads(output(text))
    if damage == 'source': value['fields'][0]['source_line'] = 999
    if damage == 'quote': value['fields'][0]['quote'] = 'fabricated quote'
    if damage == 'duplicate': value['fields'].append(value['fields'][0])
    if damage == 'name': value['fields'][0]['value'] = 'Invented Company'
    if damage == 'missing': value['fields'].pop()
    with pytest.raises(ProviderError, match='contract'):
        validate_interpretation(json.dumps(value), narrative_lines(text), 'invoice')


def test_malformed_and_oversized_narratives_are_rejected():
    assert narrative_lines('Ordinary document') is None
    for text in ('Narrative:\nx', 'Narrative:\nEnd Narrative', 'End Narrative\nNarrative:',
                 'Narrative:\n' + 'x'*4001 + '\nEnd Narrative'):
        with pytest.raises(ProviderError): narrative_lines(text)


def test_real_sdk_parsing_usage_and_job_outputs_offline(monkeypatch):
    text = narrative_text()
    requests = []
    def handler(request):
        payload = json.loads(request.content); requests.append(payload)
        assert payload['model'] == 'gpt-5-mini' and payload['store'] is False
        assert payload['max_output_tokens'] == 1024 and 'Items:' not in payload['input']
        return httpx.Response(200, json=response_body(text))
    def configure(self):
        self.settings = settings()
        if self.client is None:
            self.client = OpenAI(api_key='offline-secret', base_url=self.settings.base_url,
                max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        return self.settings
    monkeypatch.setattr(InferenceSession, 'configure', configure)
    job = process_batch(Batch(documents=[text_document('prose', text)]))
    assert job['documents'][0]['status'] == 'completed'
    assert job['documents'][0]['result']['fields']['supplier'] == 'Cedar Systems'
    assert 1 <= len(requests) <= 3
    assert job['ai_usage']['requests'] == job['ai_usage']['responses_with_usage'] == len(requests)
    assert job['ai_usage']['total_tokens'] == 180 * len(requests)
    assert 'offline-secret' not in json.dumps(job)


@pytest.mark.parametrize('status,retryable', [(401, False), (429, True), (500, True)])
def test_provider_errors_are_bounded_and_redacted(status, retryable, monkeypatch):
    session = InferenceSession('fault'); session.settings = settings()
    session.client = OpenAI(api_key='offline-secret', base_url=session.settings.base_url, max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(status,
            json={'error': {'message': 'offline-secret', 'type': 'test', 'code': 'test'}}))))
    monkeypatch.setattr(session, 'backoff', lambda *args: None)
    points = []
    with pytest.raises(ProviderError) as error:
        session.request(narrative_lines(narrative_text()), 'invoice', 'key', Budget(),
                        lambda stage, **data: points.append((stage, data)))
    assert error.value.retryable is retryable
    assert 'offline-secret' not in str(error.value) + json.dumps(points)
    assert session.total_calls == 1
    session.calls['key'] = 3
    with pytest.raises(ProviderError, match='three-request'):
        session.request([], 'invoice', 'key', Budget(), lambda *args, **kwargs: None)
    assert session.total_calls == 1
    session.close()


def test_inflight_cancellation_keeps_received_usage_and_releases_lane(monkeypatch):
    text = narrative_text(); store = JobStore()
    batch = Batch(documents=[text_document('cancel', text)])
    job_id = store.submit(batch)
    def handler(request):
        store.cancel(job_id)
        return httpx.Response(200, json=response_body(text))
    def configure(self):
        self.settings = settings()
        if self.client is None:
            self.client = OpenAI(api_key='offline-secret', base_url=self.settings.base_url, max_retries=0,
                http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        return self.settings
    monkeypatch.setattr(InferenceSession, 'configure', configure)
    store.run(job_id, batch)
    result = store.snapshot(job_id)
    assert result['status'] == 'cancelled' and not store.lane.locked()
    assert result['ai_usage']['requests'] == result['ai_usage']['responses_with_usage'] == 1
    assert result['ai_usage']['total_tokens'] == 180


def test_timeout_is_safe_and_has_no_hidden_sdk_retry(monkeypatch):
    calls = []
    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout('offline-secret', request=request)
    session = InferenceSession('timeout'); session.settings = settings()
    session.client = OpenAI(api_key='offline-secret', base_url=session.settings.base_url, max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(session, 'backoff', lambda *args: None)
    with pytest.raises(ProviderError) as error:
        session.request(narrative_lines(narrative_text()), 'invoice', 'key', Budget(), lambda *a, **k: None)
    assert error.value.retryable and len(calls) == 1
    assert 'offline-secret' not in str(error.value)
    session.close()
