import asyncio

from app.models.device import now


class EventBus:
    def __init__(self, mode: str):
        self.mode, self.sequence = mode, 0
        self.queues: set[asyncio.Queue] = set()

    def subscribe(self):
        queue = asyncio.Queue(maxsize=128)
        self.queues.add(queue)
        return queue

    def unsubscribe(self, queue):
        self.queues.discard(queue)

    async def publish(self, kind: str, **payload):
        self.sequence += 1
        event = {"type": kind, "sequence": self.sequence, "mode": self.mode, "occurred_at": now(), **payload}
        for queue in tuple(self.queues):
            if queue.full():
                # 丟棄舊事件並明確要求重新同步，避免慢速客戶端無限佔用記憶體。
                while not queue.empty():
                    queue.get_nowait()
                queue.put_nowait({"type": "resync_required", "mode": self.mode})
            else:
                queue.put_nowait(event)
