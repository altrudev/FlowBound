from __future__ import annotations

import os
import uuid
from dataclasses import asdict
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .adk_client import GoogleAdkProposalAgent
from .cloud_store import FirestoreTransitionStore
from .events import InMemoryEventPublisher, PubSubEventPublisher
from .nebius_client import NebiusNemotronProposalAgent
from .service import DeterministicDemoAgent, FlowBoundService
from .state import InMemoryCaseStore


class CreateCaseRequest(BaseModel):
    initial_state: str = "OPEN"


class RunCaseRequest(BaseModel):
    observation: str = Field(min_length=3, max_length=8000)
    human_approval_present: bool = False
    evidence_ids: list[str] = []


@lru_cache(maxsize=1)
def runtime() -> tuple[FlowBoundService, object]:
    backend = os.getenv("FLOWBOUND_BACKEND", "memory").lower()
    agent_mode = os.getenv("FLOWBOUND_AGENT_MODE", "google" if backend == "cloud" else "demo").lower()
    authorities = frozenset(
        item.strip()
        for item in os.getenv(
            "FLOWBOUND_AGENT_AUTHORITIES",
            "remediation:create,followup:schedule,case:close",
        ).split(",")
        if item.strip()
    )

    if backend == "cloud":
        project = os.environ["GOOGLE_CLOUD_PROJECT"]
        store = FirestoreTransitionStore(project=project)
        events = PubSubEventPublisher(
            project=project,
            topic_id=os.getenv("FLOWBOUND_PUBSUB_TOPIC", "flowbound-events"),
        )
    else:
        store = InMemoryCaseStore()
        events = InMemoryEventPublisher()

    if agent_mode == "google":
        agent = GoogleAdkProposalAgent()
    elif agent_mode == "nebius":
        agent = NebiusNemotronProposalAgent()
    elif agent_mode == "demo":
        agent = DeterministicDemoAgent()
    else:
        raise RuntimeError(f"Unsupported FLOWBOUND_AGENT_MODE: {agent_mode}")
    service = FlowBoundService(
        agent=agent,
        store=store,
        events=events,
        actor="flowbound_action_agent",
        actor_authorities=authorities,
    )
    return service, store


app = FastAPI(title="FlowBound", version="0.4.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "flowbound", "version": "0.4.0"}



@app.get("/api/runtime")
def runtime_info() -> dict[str, str]:
    service, _ = runtime()
    agent = service.agent
    return {
        "agent_mode": os.getenv("FLOWBOUND_AGENT_MODE", "google" if os.getenv("FLOWBOUND_BACKEND", "memory").lower() == "cloud" else "demo").lower(),
        "provider": getattr(agent, "base_url", "local"),
        "model": getattr(agent, "model", getattr(agent, "__class__", type(agent)).__name__),
        "evidence_model": getattr(agent, "evidence_model", ""),
    }


@app.post("/api/cases/{case_id}")
def create_case(case_id: str, request: CreateCaseRequest) -> dict:
    _, store = runtime()
    try:
        snapshot = store.create_case(case_id, request.initial_state)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return asdict(snapshot)


@app.get("/api/cases/{case_id}")
def get_case(case_id: str) -> dict:
    _, store = runtime()
    try:
        snapshot = store.get_case_snapshot(case_id)
        return {**asdict(snapshot), "token": snapshot.token, "recovery_required": store.is_recovery_required(case_id)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/cases/{case_id}/run")
async def run_case(case_id: str, request: RunCaseRequest) -> dict:
    service, _ = runtime()
    transition_id = f"tx-{uuid.uuid4().hex[:12]}"
    try:
        agent_proposal, outcome, assessment = await service.run_case(
            case_id=case_id,
            transition_id=transition_id,
            observation=request.observation,
            human_approval_present=request.human_approval_present,
            evidence_ids=tuple(request.evidence_ids),
            include_assessment=True,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=423, detail=str(exc)) from exc
    return {
        "transition_id": transition_id,
        "evidence_assessment": asdict(assessment),
        "agent_proposal": asdict(agent_proposal),
        "gate": asdict(outcome.gate),
        "execution": asdict(outcome.execution) if outcome.execution else None,
        "verification": asdict(outcome.verification) if outcome.verification else None,
        "event_ids": outcome.event_ids,
    }


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>FlowBound</title><style>body{font-family:system-ui;margin:0;background:#f7f8fa;color:#111827}.wrap{max-width:980px;margin:0 auto;padding:28px}.card{background:white;border:1px solid #d8dde6;border-radius:16px;padding:20px;margin:16px 0}input,textarea,button{font:inherit}input,textarea{width:100%;box-sizing:border-box;padding:12px;border:1px solid #b8c0cc;border-radius:10px}textarea{min-height:140px}button{padding:12px 18px;border:0;border-radius:10px;background:#111827;color:white;cursor:pointer}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}pre{white-space:pre-wrap;word-break:break-word;background:#0b1020;color:#e5e7eb;padding:16px;border-radius:12px;min-height:120px}.tag{font-size:12px;border:1px solid #9ca3af;border-radius:999px;padding:4px 9px}@media(max-width:720px){.grid{grid-template-columns:1fr}}</style></head>
<body><div class='wrap'><h1>FlowBound</h1><p>Governed agent execution for frontline inspection workflows. Nebius Token Factory + NVIDIA Nemotron competition path. <span class='tag'>Fortified Enterprise Fleet</span></p>
<div class='card'><label>Case ID</label><input id='case' value='demo-case-1'><p><button onclick='createCase()'>Create OPEN case</button></p></div>
<div class='card'><label>Inspector observation</label><textarea id='obs'>Rear exit door does not latch. Emergency light appears inoperative. Tenant reports the condition has persisted for three weeks.</textarea><p class='small'>Evidence trust is derived by FlowBound before model execution; the browser cannot self-assert trust.</p><button onclick='runCase()'>Run governed fleet</button></div>
<div class='grid'><div class='card'><h3>Agent + Gate</h3><pre id='result'>Waiting…</pre></div><div class='card'><h3>Current case state</h3><pre id='state'>Waiting…</pre></div></div>
<script>async function createCase(){const id=case.value;const r=await fetch('/api/cases/'+id,{method:'POST',headers:{'content-type':'application/json'},body:'{}'});result.textContent=JSON.stringify(await r.json(),null,2);await refresh()} async function refresh(){const r=await fetch('/api/cases/'+case.value);state.textContent=JSON.stringify(await r.json(),null,2)} async function runCase(){const r=await fetch('/api/cases/'+case.value+'/run',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({observation:obs.value,evidence_ids:['field-note-ui']})});result.textContent=JSON.stringify(await r.json(),null,2);await refresh()}</script>
</div></body></html>"""
