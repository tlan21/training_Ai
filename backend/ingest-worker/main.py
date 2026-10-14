"""Sequential CPU ingest: MinIO raw video → shared 1fps JPEG/WAV/features → Kafka."""
import json
import math
import os
from pathlib import Path
import re
import wave

import av
from kafka import KafkaConsumer, KafkaProducer
from minio import Minio
import numpy as np
import soundfile as sf
import torch

from ai_core.audio.features import audio_features_per_second


def preprocess(raw: Path, directory: Path) -> float:
    next_second = 0
    with av.open(str(raw)) as container:
        has_audio = bool(container.streams.audio)
        video = container.streams.video[0]
        duration = float(container.duration / av.time_base) if container.duration else float((video.duration or 0) * video.time_base)
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("invalid video duration")
        seconds = max(1, int(duration))
        for frame in container.decode(video=0):
            timestamp = float(frame.time or 0)
            if timestamp < next_second:
                continue
            frame.to_image().resize((224, 224)).save(directory / f"{next_second:08d}.jpg")
            next_second += 1
            if next_second >= seconds:
                break
    if not next_second:
        raise ValueError("no decodable video frames")
    # Keep the audio path present even for silent video; silence is data, not a fake transcript.
    with wave.open(str(directory / "audio.wav"), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        if has_audio:
            resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
            with av.open(str(raw)) as container:
                for frame in container.decode(audio=0):
                    for mono in resampler.resample(frame):
                        output.writeframes(mono.to_ndarray().tobytes())
                for mono in resampler.resample(None):
                    output.writeframes(mono.to_ndarray().tobytes())
        else:
            remaining = int(duration * 16000)
            while remaining:
                count = min(remaining, 16000)
                output.writeframes(bytes(count * 2))
                remaining -= count
    features = []
    with sf.SoundFile(directory / "audio.wav") as audio:
        while True:
            samples = audio.read(120 * 16000, dtype="float32")
            if not len(samples):
                break
            if len(samples) < 16000:
                samples = np.pad(samples, (0, 16000 - len(samples)))
            features.extend(audio_features_per_second(torch.from_numpy(samples), sr=16000).tolist())
    aligned = min(next_second, len(features))
    if not aligned:
        raise ValueError("missing aligned audio/video features")
    for extra in range(aligned, next_second):
        (directory / f"{extra:08d}.jpg").unlink()
    (directory / "audio_features.json").write_text(json.dumps(features[:aligned]), encoding="utf-8")
    return duration


def main():
    torch.set_num_threads(2)
    work = Path("/srv/work")
    work.mkdir(exist_ok=True)
    storage = Minio(os.environ["MINIO_ENDPOINT"], access_key=os.environ["MINIO_ACCESS_KEY"],
                    secret_key=os.environ["MINIO_SECRET_KEY"], secure=False)
    brokers = os.environ["KAFKA_BROKERS"].split(",")
    producer = KafkaProducer(bootstrap_servers=brokers, value_serializer=lambda x: json.dumps(x).encode())
    consumer = KafkaConsumer("video.uploaded", bootstrap_servers=brokers, group_id="ingest-worker",
                             auto_offset_reset="earliest", enable_auto_commit=False,
                             max_poll_records=1, max_poll_interval_ms=2*60*60*1000)
    for message in consumer:
        req = json.loads(message.value)
        video_id = req["video_id"]
        if not re.fullmatch(r"vid_[A-Za-z0-9_]+", video_id):
            print("[ingest] rejected invalid video id", flush=True)
            consumer.commit()
            continue
        directory = work / video_id
        directory.mkdir(exist_ok=True)
        duration = 0.0
        try:
            bucket, key = req["raw_file_path"].split("/", 1)
            raw = directory / "raw.mp4"
            storage.fget_object(bucket, key, str(raw))
            duration = preprocess(raw, directory)
            raw.unlink()
        except Exception as exc:
            (directory / "error.txt").write_text(str(exc), encoding="utf-8")
            print(f"[ingest] {video_id} failed: {exc}", flush=True)
        # Zero duration explicitly marks failed preprocessing; the Go consumer records error.txt in the job.
        producer.send("video.preprocessed", key=video_id.encode(), value={
            "video_id": video_id, "duration": duration, "keyframes_path": str(directory),
            "audio_path": str(directory / "audio.wav"),
        }).get(timeout=30)
        consumer.commit()
        print(f"[ingest] {video_id}: {duration}s", flush=True)


if __name__ == "__main__":
    main()
