"""No server/dependencies: verify fresh JSON schema and preservation of existing collections."""
import importlib.util
import pathlib
import sys
import types
import unittest
from unittest.mock import Mock, patch

class FrameSchemaTest(unittest.TestCase):
    def test_create_load_only_frame_collection_and_preserve_existing(self):
        created = []
        column = Mock()
        sdk = types.ModuleType('pymilvus')
        sdk.DataType = types.SimpleNamespace(INT64='Int64', FLOAT_VECTOR='FloatVector', JSON='JSON')
        sdk.FieldSchema = lambda **fields: fields
        sdk.CollectionSchema = lambda fields, **kw: fields
        def collection(name, schema):
            created.append((name, schema))
            return column
        sdk.Collection = collection
        sdk.connections = Mock()
        sdk.utility = Mock()
        sdk.utility.has_collection.return_value = False
        with patch.dict(sys.modules, {'pymilvus': sdk}):
            spec = importlib.util.spec_from_file_location('init_frames', pathlib.Path(__file__).with_name('init_collections.py'))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.main()
            self.assertEqual([x[0] for x in created], ['video_frame_embeddings'])
            self.assertEqual([x['name'] for x in created[0][1]], ['id', 'vector', 'payload'])
            self.assertEqual(created[0][1][2]['dtype'], 'JSON')
            column.load.assert_called_once()
            sdk.utility.has_collection.return_value = True
            module.main()
            self.assertEqual(len(created), 1, 'Existing data must not be recreated or dropped')

if __name__ == '__main__':
    unittest.main()
