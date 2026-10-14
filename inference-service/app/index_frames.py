"""Backfill explicit processed video IDs: python -m app.index_frames vid_..."""
import argparse
import importlib.util
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from .registry import registry
from .visual_index import index_frames


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video_ids", nargs="+")
    args = parser.parse_args()
    registry.load_all()
    for video_id in args.video_ids:
        if not re.fullmatch(r"vid_[A-Za-z0-9_]{1,46}", video_id):
            raise ValueError("Invalid video ID")
        frames = sorted((Path("/srv/work") / video_id).glob("[0-9]" * 8 + ".jpg"))
        if frames:
            count = index_frames([str(path) for path in frames])
        else:
            # T4.1 removes scratch frames; reuse the original MinIO object and the same ingest sampler.
            from minio import Minio
            storage = Minio(os.environ["MINIO_ENDPOINT"], access_key=os.environ["MINIO_ACCESS_KEY"],
                            secret_key=os.environ["MINIO_SECRET_KEY"], secure=False)
            spec = importlib.util.spec_from_file_location("ingest", "/srv/ingest-worker/main.py")
            ingest = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ingest)
            with TemporaryDirectory(prefix="siamese-backfill-") as tmp:
                directory = Path(tmp)
                raw = directory / "raw.mp4"
                storage.fget_object("raw-videos", f"{video_id}.mp4", str(raw))
                ingest.preprocess(raw, directory)
                frames = sorted(directory.glob("[0-9]" * 8 + ".jpg"))
                count = index_frames([str(path) for path in frames], video_id=video_id)
        print(f"{video_id}: indexed {count} Siamese frames", flush=True)


if __name__ == "__main__":
    main()
