import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import wave

import av
import numpy as np
import torch

from main import connect_kafka, preprocess
from kafka.errors import KafkaTimeoutError, KafkaConnectionError


class PreprocessTest(unittest.TestCase):
    def test_packaged_cpu_only_sources(self):
        root = Path("/srv")
        self.assertEqual(torch.version.cuda, None)
        self.assertTrue(torch.__version__.endswith("+cpu"))
        self.assertFalse((root / "inference-service").exists())
        self.assertEqual(sorted(str(p.relative_to(root / "ai_core")) for p in (root / "ai_core").rglob("*.py")),
                         ["audio/features.py", "audio/mel.py"])
        self.assertFalse(any(root.rglob("*.pt")))

    def check_output(self, directory, duration):
        features = np.asarray(json.loads((directory / "audio_features.json").read_text()))
        frames = sorted(directory.glob("*.jpg"))
        self.assertEqual(features.shape, (len(frames), 64))
        self.assertGreater(len(frames), 0)
        self.assertTrue(np.isfinite(features).all())
        self.assertLessEqual(len(frames), max(1, int(duration)))
        self.assertEqual([p.name for p in frames], [f"{i:08d}.jpg" for i in range(len(frames))])
        with wave.open(str(directory / "audio.wav")) as audio:
            self.assertEqual((audio.getframerate(), audio.getnchannels(), audio.getsampwidth()), (16000, 1, 2))
            self.assertGreater(audio.getnframes(), 0)

    def test_existing_fixture_with_audio(self):
        with av.open("/fixtures/video.mp4") as source:
            self.assertGreater(len(source.streams.audio), 0)
        with tempfile.TemporaryDirectory() as work, patch.object(torch, "load", side_effect=AssertionError("No checkpoint in ingest")):
            directory = Path(work)
            duration = preprocess(Path("/fixtures/video.mp4"), directory)
            self.check_output(directory, duration)
            self.assertFalse(any(name.startswith("ai_core.models") for name in sys.modules))

    def test_silent_fractional_video(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            raw = root / "silent.mp4"
            with av.open(str(raw), "w") as container:
                stream = container.add_stream("mpeg4", rate=10)
                stream.width, stream.height, stream.pix_fmt = 64, 64, "yuv420p"
                for _ in range(25):
                    frame = av.VideoFrame.from_ndarray(np.zeros((64, 64, 3), dtype=np.uint8), format="rgb24")
                    container.mux(stream.encode(frame))
                container.mux(stream.encode(None))
            directory = root / "output"
            directory.mkdir()
            duration = preprocess(raw, directory)
            self.assertAlmostEqual(duration, 2.5)
            self.check_output(directory, duration)
            with wave.open(str(directory / "audio.wav")) as audio:
                self.assertEqual(set(audio.readframes(audio.getnframes())), {0})

    def test_invalid_video_fails(self):
        with tempfile.TemporaryDirectory() as work:
            directory = Path(work)
            raw = directory / "invalid.mp4"
            raw.write_bytes(b"not a video")
            with self.assertRaises(av.error.InvalidDataError):
                preprocess(raw, directory)
            self.assertFalse((directory / "audio_features.json").exists())


class BootstrapTest(unittest.TestCase):
    def test_producer_recovers_without_changing_consumer_contract(self):
        producer, consumer = Mock(), Mock()
        with patch("main.KafkaProducer", side_effect=[KafkaConnectionError(), producer]) as create, \
                patch("main.KafkaConsumer", return_value=consumer) as consume, \
                patch("main.time.monotonic", return_value=0), patch("main.time.sleep") as sleep:
            self.assertEqual(connect_kafka(["kafka:9092"]), (producer, consumer))
            self.assertEqual(create.call_count, 2)
            sleep.assert_called_once_with(2)
            self.assertEqual(consume.call_args.args, ("video.uploaded",))
            self.assertEqual(consume.call_args.kwargs["group_id"], "ingest-worker")
            self.assertFalse(consume.call_args.kwargs["enable_auto_commit"])

    def test_consumer_bootstrap_failure_closes_partial_producer(self):
        first, producer, consumer = Mock(), Mock(), Mock()
        with patch("main.KafkaProducer", side_effect=[first, producer]), \
                patch("main.KafkaConsumer", side_effect=[KafkaTimeoutError(), consumer]), \
                patch("main.time.monotonic", return_value=0), patch("main.time.sleep"):
            self.assertEqual(connect_kafka(["kafka:9092"]), (producer, consumer))
            first.close.assert_called_once_with(timeout=0)
            producer.close.assert_not_called()

    def test_deadline_fails_without_unbounded_retry(self):
        with patch("main.KafkaProducer", side_effect=KafkaConnectionError()) as create, \
                patch("main.time.monotonic", side_effect=[0, 91]), patch("main.time.sleep") as sleep:
            with self.assertRaises(KafkaConnectionError):
                connect_kafka(["kafka:9092"])
            self.assertEqual(create.call_count, 1)
            sleep.assert_not_called()

    def test_permanent_config_error_closes_producer_and_fails_immediately(self):
        producer = Mock()
        with patch("main.KafkaProducer", return_value=producer), \
                patch("main.KafkaConsumer", side_effect=ValueError("invalid config")), \
                patch("main.time.sleep") as sleep:
            with self.assertRaises(ValueError):
                connect_kafka(["kafka:9092"])
            producer.close.assert_called_once_with(timeout=0)
            sleep.assert_not_called()


if __name__ == "__main__":
    torch.set_num_threads(1)
    unittest.main()
