from ai_core.scripts.prepare_news_summary import record


def test_news_record_removes_repeated_title_and_groups_same_body():
    body = "Tin tức mới nhất " + "Nội dung của bài báo. " * 25
    row = {"title": "Tin tức mới nhất", "summary": "Sapo", "content": body}
    a = record(row)
    assert a and not a["body"].startswith(row["title"])
    b = record({**row, "title": "Tiêu đề khác biệt", "content": a["body"]})
    assert a["id"] == b["id"]
    assert record({**row, "content": "too short"}) is None


def test_zero_temperature_is_greedy_even_with_ties():
    import torch
    from ai_core.config import ModelConfig
    from ai_core.models.minigpt import MiniGPT

    model = MiniGPT(ModelConfig(name="minigpt", d_model=16, n_layers=1,
                               n_heads=2, vocab_size=8, context_len=16))
    with torch.no_grad():
        for p in model.parameters():
            p.zero_()
    prompt = torch.tensor([[1, 2]])
    out = model.generate(prompt, max_new_tokens=3, temperature=0)
    assert out.tolist() == [[1, 2, 0, 0, 0]]
    # Dividing fp16 logits by 1e-5 overflows distinct scores into indistinguishable +inf.
    model.embed.logits = lambda x: torch.tensor([[[1., 2., 0., 0., 0., 0., 0., 0.]]], dtype=torch.float16)
    assert model.generate(prompt, max_new_tokens=1, temperature=0).tolist() == [[1, 2, 1]]


def test_news_evaluation_uses_full_lead_sentence_and_eos_prefix():
    import torch
    from ai_core.tokenizer import BPETokenizer
    from ai_core.scripts.finetune_news_summary import evaluate

    tok = BPETokenizer()
    first = "A complete first sentence " + "with details " * 8 + "."
    row = {"id": "one", "title": "correct headline", "summary": first + " Next sentence.", "body": "Body."}

    class FixedOutput:
        def eval(self):
            return self

        def generate(self, prompt, _budget, temperature, eos_id):
            assert prompt[0, -1] == eos_id and temperature == 0
            output = torch.tensor([tok.encode(row["title"]) + [eos_id]])
            return torch.cat([prompt, output], dim=1)

    result = evaluate(FixedOutput(), [row], tok, torch.device("cpu"))[0]
    assert result["rouge_l"] == 1.0
    assert result["lead1"] == first and len(result["lead1"]) > 80
