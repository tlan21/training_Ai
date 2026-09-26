"""Hàng đợi GPU tuần tự: asyncio queue + 1 worker (master plan §2.4).

Mọi job GPU (vision/asr/highlight/completions) chạy lần lượt qua 1 worker để không
tranh VRAM trên 1 card. Search/recommendation nhẹ nhưng vẫn xếp hàng để đo queue_depth.
"""

import asyncio
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


class GPUQueue:
    def __init__(self) -> None:
        # Queue tạo lazy trong start() để bind đúng event loop đang chạy
        # (asyncio.Queue bind loop lúc khởi tạo → tạo ở import sẽ lệch loop).
        self._queue: asyncio.Queue | None = None
        self._worker: asyncio.Task | None = None

    def start(self) -> None:
        if self._worker is None:
            self._queue = asyncio.Queue()
            self._worker = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                pass
            self._worker = None
            self._queue = None

    @property
    def depth(self) -> int:
        return 0 if self._queue is None else self._queue.qsize()

    async def submit(self, fn: Callable[[], T]) -> T:
        """Đưa job (hàm sync, chạy trong thread để không chặn event loop) vào hàng đợi, chờ kết quả."""
        if self._queue is None:
            raise RuntimeError("GPUQueue chưa start()")
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        await self._queue.put((fn, fut))
        return await fut

    async def _run(self) -> None:
        while True:
            fn, fut = await self._queue.get()
            try:
                # chạy job blocking trong thread pool → tuần tự vì 1 worker rút hàng đợi
                result = await asyncio.to_thread(fn)
                if not fut.done():
                    fut.set_result(result)
            except Exception as e:  # noqa: BLE001 — propagate về caller
                if not fut.done():
                    fut.set_exception(e)
            finally:
                self._queue.task_done()


gpu_queue = GPUQueue()
