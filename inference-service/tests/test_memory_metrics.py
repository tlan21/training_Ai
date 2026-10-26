import io

from app.registry import ModelRegistry


def test_cpu_memory_cannot_be_misreported_as_cuda_pass(monkeypatch):
    registry = ModelRegistry()
    registry.device = "cpu"
    monkeypatch.setattr("builtins.open", lambda *args,**kwargs: io.StringIO("VmRSS:\t2048 kB\nVmHWM:\t3072 kB\n"))
    sample = registry.memory_snapshot()
    assert sample["rss_bytes"] == 2*1024**2
    assert sample["rss_peak_bytes"] == 3*1024**2
    assert sample["cuda_peak_reserved_bytes"] is None
    assert sample["cuda_allocated_bytes"] is None


def test_cuda_metrics_keep_allocated_reserved_and_peak_separate(monkeypatch):
    import torch
    registry = ModelRegistry()
    registry.device = "cuda"
    monkeypatch.setattr("builtins.open", lambda *args,**kwargs: io.StringIO("VmRSS:\t2048 kB\nVmHWM:\t3072 kB\n"))
    for name,value in [("memory_allocated",10),("memory_reserved",20),
                       ("max_memory_allocated",30),("max_memory_reserved",40)]:
        monkeypatch.setattr(torch.cuda,name,lambda value=value:value)
    sample = registry.memory_snapshot()
    assert sample["cuda_allocated_bytes"] == 10
    assert sample["cuda_reserved_bytes"] == 20
    assert sample["cuda_peak_allocated_bytes"] == 30
    assert sample["cuda_peak_reserved_bytes"] == 40
