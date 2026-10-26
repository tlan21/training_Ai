"""Create/validate an empty AI-09 sandbox; never load data or touch product collections."""
import json
import os

from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

NAME = "sandbox_two_tower_ai09_20261026"


def main():
    host = os.environ.get("MILVUS_HOST", "127.0.0.1")
    port = os.environ.get("MILVUS_PORT", "19530")
    connections.connect(host=host, port=port)
    if not utility.has_collection(NAME):
        col = Collection(NAME, CollectionSchema([
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=50, is_primary=True, auto_id=False),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=128),
            FieldSchema(name="type", dtype=DataType.VARCHAR, max_length=10),
        ], description="CODEX AI-09 sandbox only; never product data"))
        col.create_index("vector", {"index_type": "IVF_FLAT", "metric_type": "IP", "params": {"nlist": 1024}})
    else:
        col = Collection(NAME)
    fields = {field.name: field for field in col.schema.fields}
    assert set(fields) == {"id", "vector", "type"}, "Existing sandbox schema mismatch; leave it intact"
    assert fields["id"].dtype == DataType.VARCHAR and fields["id"].is_primary
    assert not fields["id"].to_dict().get("auto_id", False) and int(fields["id"].params["max_length"]) == 50
    assert fields["vector"].dtype == DataType.FLOAT_VECTOR and int(fields["vector"].params["dim"]) == 128
    assert fields["type"].dtype == DataType.VARCHAR and int(fields["type"].params["max_length"]) == 10
    index = next(index.params for index in col.indexes if index.field_name == "vector")
    assert index["index_type"] == "IVF_FLAT" and index["metric_type"] == "IP" and int(index["params"]["nlist"]) == 1024
    print(json.dumps({"collection": NAME, "host": host, "port": port, "dimension": 128,
                      "index": index, "entities": col.num_entities, "schema_verified": True}))


if __name__ == "__main__":
    main()
