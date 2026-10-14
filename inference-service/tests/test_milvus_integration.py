"""Opt-in T4.2 check against the retained real corpus; does not insert or delete user data."""
import json
import os
from pathlib import Path
import time

import numpy as np
import pytest

from app import services, visual_index


@pytest.mark.skipif(os.environ.get("T42_INTEGRATION") != "1", reason="requires real Milvus corpus")
def test_real_hnsw_ef_sweep_and_cosine_ground_truth(monkeypatch):
    monkeypatch.setattr(services.settings, "force_stub", False)
    services.registry.load_all()
    assert not services.registry.stub_mode
    col = visual_index.collection()
    col.flush(timeout=30)
    from pymilvus import utility
    utility.wait_for_index_building_complete(visual_index.COLLECTION, using="visual", timeout=60)
    col.release(timeout=30)
    col.load(timeout=30)
    rows = col.query(expr="id >= 0", output_fields=["id", "vector", "payload"], limit=1000, consistency_level="Strong", timeout=5)
    assert len(rows) >= 8
    vectors = np.asarray([row["vector"] for row in rows], dtype=np.float32)
    ids = [row["id"] for row in rows]
    k = min(10,len(rows))
    sweep = []
    # Record the first search separately; steady-state tuning excludes collection-load warmup.
    start = time.perf_counter()
    col.search([vectors[0].tolist()],"vector",{"metric_type":"COSINE","params":{"ef":100}},
               limit=k,consistency_level="Session",timeout=1)
    first_search_ms = (time.perf_counter()-start)*1000
    # Stored vectors isolate HNSW approximation from image/model preprocessing.
    for ef in [64,100,128,256]:
        latencies, recalls = [], []
        for vector in vectors[:20]:
            truth_scores = vectors @ vector / (np.linalg.norm(vectors,axis=1)*np.linalg.norm(vector))
            cutoff = np.sort(truth_scores)[-k]
            truth = {ids[i] for i,score in enumerate(truth_scores) if score >= cutoff-1e-6}
            start = time.perf_counter()
            found = col.search([vector.tolist()],"vector",{"metric_type":"COSINE","params":{"ef":ef}},
                                   limit=k,consistency_level="Session",timeout=1)[0]
            latencies.append((time.perf_counter()-start)*1000)
            recalls.append(sum(hit.id in truth for hit in found)/k)
        sweep.append({"ef":ef,"mean_recall_at_10_ties":float(np.mean(recalls)),
                      "p95_ms":float(np.percentile(latencies,95)),"max_ms":max(latencies)})
    progress = utility.index_building_progress(visual_index.COLLECTION,using="visual")
    report = {"device":services.registry.device,"live_rows":len(rows),"index":col.indexes[0].params,
              "index_progress":progress,"sweep":sweep,
              "first_search_after_load_ms":first_search_ms,
              "consistency":"Session", "selected_ef":100,
              "reason":"gateway top_k=100 requires ef>=100; smallest passing setting"}
    Path("/tmp/t42-hnsw.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    assert progress["indexed_rows"] >= len(rows), progress
    assert all(result["mean_recall_at_10_ties"] >= .99 for result in sweep)
    assert next(result for result in sweep if result["ef"] == 100)["p95_ms"] < 200
