import asyncio
import gc
import weakref

from app.gpu_queue import GPUQueue


def test_idle_worker_releases_completed_job_and_response():
    class Response:
        def __init__(self):
            self.data = bytearray(1024*1024)
    class Job:
        def __call__(self):
            return Response()
    async def check():
        queue = GPUQueue()
        queue.start()
        try:
            job = Job()
            job_ref = weakref.ref(job)
            response = await queue.submit(job)
            response_ref = weakref.ref(response)
            del job, response
            await asyncio.sleep(0)
            gc.collect()
            assert job_ref() is None, "idle GPU worker retains last request closure"
            assert response_ref() is None, "idle GPU worker retains last response"
            assert queue.depth == 0
        finally:
            await queue.stop()
    asyncio.run(check())


def test_queue_propagates_failure_then_processes_next_job():
    async def check():
        queue = GPUQueue()
        queue.start()
        def fail():
            raise ValueError("model failed")
        try:
            try:
                await queue.submit(fail)
            except ValueError as exc:
                assert str(exc) == "model failed"
            else:
                raise AssertionError("queue swallowed model error")
            assert await queue.submit(lambda: 42) == 42
        finally:
            await queue.stop()
    asyncio.run(check())
