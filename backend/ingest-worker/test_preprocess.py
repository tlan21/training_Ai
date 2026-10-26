import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

import av
import numpy as np
import torch

from main import preprocess


class PreprocessTest(unittest.TestCase):
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


if __name__ == "__main__":
    torch.set_num_threads(1)
    unittest.main()
