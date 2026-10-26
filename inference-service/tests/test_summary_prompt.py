from types import SimpleNamespace

import pytest
import torch

from ai_core.tokenizer import BPETokenizer
from ai_core.training.datasets.summary_dataset import CONTROL_TOKENS, summary_prompt_ids
from app import schemas, services


def setup_model(monkeypatch):
    tok, calls = BPETokenizer(), []

    class Model:
        cfg = SimpleNamespace(context_len=1024)

        def generate(self, prompt, max_new_tokens, temperature, eos_id):
            ids = prompt[0].tolist()
            assert len(ids) + 96 <= 512 and ids[-1] == eos_id
            calls.append((ids, max_new_tokens))
            output = tok.encode("ban tom tat " * 6)[:max_new_tokens - 1] + [eos_id]
            return torch.cat([prompt, torch.tensor([output])], dim=1)

    monkeypatch.setattr(services.registry, "tokenizer", tok)
    monkeypatch.setattr(services.registry, "models", {"minigpt": Model()})
    monkeypatch.setattr(services.registry, "minigpt_metadata", {"summary_context_len": 512, "max_target_tokens": 96})
    monkeypatch.setattr(services.registry, "device", "cpu")
    return tok, calls


@pytest.mark.parametrize("fmt", ["sum", "title", "cap"])
def test_short_prompt_matches_training_and_caps_output(monkeypatch, fmt):
    tok, calls = setup_model(monkeypatch)
    source = "Nội dung tiếng Việt thật."
    services._real_summarize(schemas.CompletionRequest(prompt=CONTROL_TOKENS[fmt] + " " + source, max_tokens=256))
    assert calls == [(summary_prompt_ids(source, tok, fmt, 512, 96), 96)]


def test_raw_backend_prompt_defaults_to_sum(monkeypatch):
    tok, calls = setup_model(monkeypatch)
    services._real_summarize(schemas.CompletionRequest(prompt="xin chao", max_tokens=5))
    assert calls == [(summary_prompt_ids("xin chao", tok, "sum", 512, 96), 5)]


def test_actual_ctc_uppercase_matches_asr_training_case(monkeypatch):
    tok, calls = setup_model(monkeypatch)
    services._real_summarize(schemas.CompletionRequest(prompt="TÔI ĐANG HỌC TIẾNG VIỆT"))
    assert calls[0][0] == summary_prompt_ids("tôi đang học tiếng việt", tok, "sum", 512, 96)


def test_empty_map_outputs_do_not_invent_a_reduce_summary(monkeypatch):
    _, calls = setup_model(monkeypatch)
    model = services.registry.models["minigpt"]
    monkeypatch.setattr(model, "generate", lambda prompt, **_: torch.cat([prompt, torch.tensor([[258]])], dim=1))
    assert services._real_summarize(schemas.CompletionRequest(prompt="long input " * 1000)) == ""


def test_multilevel_reduce_keeps_every_source_token(monkeypatch):
    tok, calls = setup_model(monkeypatch)
    source = "begin " + "noi dung dai " * 2000 + " end"
    source_ids = tok.encode(" " + source)
    cap = 512 - 96 - 1 - len(tok.encode("<sum>"))
    services._real_summarize(schemas.CompletionRequest(prompt=source, max_tokens=12))
    first_level = (len(source_ids) + cap - 1) // cap
    seen = [token for ids, _ in calls[:first_level] for token in ids[len(tok.encode("<sum>")):-1]]
    assert seen == source_ids
    assert len(calls) > first_level + 1  # More than one reduction level was required.
    assert calls[-1][1] == 12


def test_invalid_profile_fails_and_silence_does_not_hallucinate(monkeypatch):
    _, calls = setup_model(monkeypatch)
    assert services._real_summarize(schemas.CompletionRequest(prompt="  ")) == ""
    assert calls == []
    monkeypatch.setattr(services.registry, "minigpt_metadata", {"summary_context_len": 64, "max_target_tokens": 96})
    with pytest.raises(RuntimeError, match="metadata"):
        services._real_summarize(schemas.CompletionRequest(prompt="xin chao"))


def test_completion_rejects_invalid_decoding_parameters():
    from pydantic import ValidationError
    for parameters in ({"max_tokens": 0}, {"temperature": -1}, {"temperature": float("nan")}):
        with pytest.raises(ValidationError):
            schemas.CompletionRequest(prompt="xin chao", **parameters)


def test_registry_reload_clears_previous_summary_profile(monkeypatch):
    from app.registry import ModelRegistry
    reg = ModelRegistry()
    reg.tokenizer = object()
    reg.minigpt_metadata = {"summary_context_len": 512}
    monkeypatch.setattr(services.settings, "force_stub", True)
    reg.load_all()
    assert reg.tokenizer is None and reg.minigpt_metadata == {}
