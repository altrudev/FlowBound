from __future__ import annotations

import json
from typing import Any


class PubSubEventPublisher:
    """Publish FlowBound workflow events through Google Cloud Pub/Sub."""

    def __init__(
        self,
        *,
        project: str,
        topic_id: str,
        client: Any | None = None,
    ) -> None:
        if client is None:
            from google.cloud import pubsub_v1

            client = pubsub_v1.PublisherClient()
        self._client = client
        self._topic_path = client.topic_path(project, topic_id)

    def publish(self, event_type: str, payload: dict[str, Any]) -> str:
        body = {
            "event_type": event_type,
            "payload": payload,
        }
        data = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        future = self._client.publish(self._topic_path, data=data, event_type=event_type)
        return future.result(timeout=10)
