"""Graceful shutdown coordination for AIOS vNext runtime resources."""
import asyncio
class ShutdownManager:
    def __init__(self): self._tasks=set(); self._closers=[]; self._release_callbacks=[]; self._closed=False
    def track_task(self, task):
        if self._closed: task.cancel(); return task
        self._tasks.add(task); task.add_done_callback(self._tasks.discard); return task
    def register(self, resource):
        if not self._closed: self._closers.append(resource)
        return resource
    def register_release(self, callback):
        if not self._closed: self._release_callbacks.append(callback)
        return callback
    async def shutdown(self):
        if self._closed: return
        self._closed=True; tasks=list(self._tasks)
        for task in tasks: task.cancel()
        if tasks: await asyncio.gather(*tasks,return_exceptions=True)
        for callback in reversed(self._release_callbacks):
            result=callback()
            if asyncio.iscoroutine(result): await result
        for resource in reversed(self._closers):
            close=getattr(resource,"aclose",None) or getattr(resource,"close",None)
            if close:
                result=close()
                if asyncio.iscoroutine(result): await result
        self._tasks.clear(); self._release_callbacks.clear(); self._closers.clear()
