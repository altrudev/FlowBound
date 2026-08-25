import json

from flowbound.cloud_store import FirestoreTransitionStore
from flowbound.events import PubSubEventPublisher
from flowbound.gate import Decision, GateResult, TransitionProposal
from flowbound.workflow import process_transition


class FakeDocument:
    def __init__(self, sink, path):
        self.sink = sink
        self.path = path

    def collection(self, name):
        return FakeCollection(self.sink, f"{self.path}/{name}")

    def set(self, payload):
        self.sink[self.path] = payload


class FakeCollection:
    def __init__(self, sink, path):
        self.sink = sink
        self.path = path

    def document(self, name):
        return FakeDocument(self.sink, f"{self.path}/{name}")


class FakeFirestoreClient:
    def __init__(self):
        self.documents = {}

    def collection(self, name):
        return FakeCollection(self.documents, name)


class FakeFuture:
    def result(self, timeout=None):
        return "message-123"


class FakePublisherClient:
    def __init__(self):
        self.calls = []

    def topic_path(self, project, topic_id):
        return f"projects/{project}/topics/{topic_id}"

    def publish(self, topic_path, *, data, **attributes):
        self.calls.append((topic_path, data, attributes))
        return FakeFuture()


def proposal():
    return TransitionProposal(
        actor="action-agent",
        predecessor_state="OPEN",
        observed_state="OPEN",
        requested_effect="CREATE_REMEDIATION",
        allowed_effects=frozenset({"CREATE_REMEDIATION"}),
        actor_authorities=frozenset({"remediation:create"}),
        required_authority="remediation:create",
    )


def test_firestore_store_records_transition_with_serializable_sets():
    client = FakeFirestoreClient()
    store = FirestoreTransitionStore(client=client)
    result = GateResult(Decision.ALLOW, "ok")

    store.record_decision(
        case_id="case-1",
        transition_id="tx-1",
        proposal=proposal(),
        result=result,
    )

    saved = client.documents["cases/case-1/transitions/tx-1"]
    assert saved["decision"] == "ALLOW"
    assert saved["proposal"]["allowed_effects"] == ["CREATE_REMEDIATION"]


def test_pubsub_publisher_emits_json_event():
    client = FakePublisherClient()
    publisher = PubSubEventPublisher(
        project="demo-project",
        topic_id="flowbound-events",
        client=client,
    )

    message_id = publisher.publish("flowbound.test", {"case_id": "case-1"})

    assert message_id == "message-123"
    topic, data, attributes = client.calls[0]
    assert topic == "projects/demo-project/topics/flowbound-events"
    assert attributes["event_type"] == "flowbound.test"
    assert json.loads(data)["payload"]["case_id"] == "case-1"


def test_workflow_persists_and_publishes_gate_result():
    firestore_client = FakeFirestoreClient()
    publisher_client = FakePublisherClient()
    store = FirestoreTransitionStore(client=firestore_client)
    events = PubSubEventPublisher(
        project="demo-project",
        topic_id="flowbound-events",
        client=publisher_client,
    )

    result = process_transition(
        case_id="case-9",
        transition_id="tx-7",
        proposal=proposal(),
        store=store,
        events=events,
    )

    assert result.decision is Decision.ALLOW
    assert "cases/case-9/transitions/tx-7" in firestore_client.documents
    published = json.loads(publisher_client.calls[0][1])
    assert published["payload"]["decision"] == "ALLOW"
