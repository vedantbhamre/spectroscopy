"""End-to-end graph test with a scripted LLM: the deterministic safeguards must hold whatever the model says."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.gateway.client import LLMResult

H04 = next(s for s in json.loads((Path(__file__).parent.parent / "data" / "scenarios.json").read_text()) if s["id"] == "H04")["enquiry"]

ANALYST = {
    "stated": [
        {"fact": "Water content in a petroleum line", "quote": "water content in a petroleum line"},
        {"fact": "Existing silica cable", "quote": "We already have a silica fiber cable"},
        {"fact": "Invented fact", "quote": "the line runs at 80 °C"},  # not said: must be dropped
    ],
    "unknowns": ["link length", "routing", "operating conditions"],
    "target_variables": ["water content"],
    "methods_requested": ["MIR_ATR"],
    "fibers_mentioned": ["silica_visnir"],
    "use_context": "process",
    "asks_for_certainty": True,
}

RESPONDER = {
    "reply": "Approved.",
    "title": "Silica link for MIR ATR",
    "decisionStatus": "provisional",  # contradicts the failed fibre check: must be lowered
    "requirements": {"stated": ["Water in petroleum"], "unknowns": ["Link length"]},
    "questions": [{"text": "What is the link length?", "impact": "setup"}],
    "recommendations": [{
        "method": "MIR ATR", "methodIds": ["MIR_ATR", "THZ"], "role": "primary", "reason": "Water in petroleum is a supplied application.",
        "citations": [
            {"source": "S02", "page": "13", "quote": "Application: measurement of water content in petroleum"},
            {"source": "S02", "page": "13", "quote": "Silica fibres transmit the full mid-IR range without loss"},
        ],
    }],
    "concept": {"summary": "ATR probe in the line.", "citations": [{"source": "S01", "page": "p.9", "quote": "Vibrational spectroscopy in the mid-IR range (4000–400 cm-1) is one of the most informative methods of chemical analysis."}]},
    "spectralRange": {"summary": "4000–400 cm-1.", "citations": []},
    "risks": ["Fouling"],
    "feasibility": {"steps": ["Lab samples"], "decisionBasis": "Client criteria."},
}


@pytest.fixture
def client(monkeypatch):
    def fake_chat(messages, *, json_mode=False, feature="assess", **_):
        payload = {"planner": {"intent": "assessment", "queries": ["MIR ATR water petroleum silica fiber"]},
                   "analyst": ANALYST, "responder": RESPONDER}.get(feature)
        text = json.dumps(payload) if payload is not None else "It is the link between the analyser and the probe."
        return LLMResult(text=text, model="fake", via="test", ms=1)

    import app.agents.nodes.analyst as analyst
    import app.agents.nodes.planner as planner
    import app.agents.nodes.responder as responder

    for mod in (planner, analyst, responder):
        monkeypatch.setattr(mod, "chat", fake_chat)
    from app.main import app

    return TestClient(app)


def test_h04_safeguards(client):
    r = client.post("/assess", json={"messages": [{"role": "user", "content": H04}], "scenarioId": "H04"})
    assert r.status_code == 200, r.text
    body = r.json()
    rep = body["report"]

    assert rep["decisionStatus"] == "insufficient"  # floor from the failed fibre check
    assert any(c["id"] == "fiber_silica_visnir_MIR_ATR" and c["status"] == "fail" for c in rep["premiseChecks"])
    cites = rep["recommendations"][0]["citations"]
    assert [c["check"] for c in cites] == ["verified", "failed"]  # invented quote is exposed
    assert rep["recommendations"][0]["methodIds"] == ["MIR_ATR"]  # unknown method dropped
    assert rep["concept"]["citations"][0]["page"] == "9" and rep["concept"]["citations"][0]["check"] == "verified"
    assert rep["origin"] == "live" and rep["scenarioId"] == "H04"
    assert "null" not in r.text  # frontend zod .optional() rejects null

    steps = {t["step"]: t for t in body["trace"]}
    assert steps["Safety gate"]["status"] == "warn" and "approval_demand" in steps["Safety gate"]["detail"]  # flag, not a block
    assert "1 unquoted dropped" in steps["Separate facts and unknowns"]["detail"]
    assert steps["Premise checks"]["status"] == "fail"
    assert "1 not found" in steps["Verify citations"]["detail"]


def test_followup_question_uses_memory(client, monkeypatch):
    first = [{"role": "user", "content": H04}]
    assert client.post("/assess", json={"messages": first}).status_code == 200

    import app.agents.nodes.planner as planner

    monkeypatch.setattr(planner, "chat", lambda *a, **k: LLMResult(json.dumps({"intent": "conversational", "queries": []}), "fake", "test", 1))
    follow = first + [{"role": "assistant", "content": "Report ready."}, {"role": "user", "content": "What does fibre link mean?"}]
    r = client.post("/assess", json={"messages": follow})
    assert r.status_code == 200
    body = r.json()
    assert body["reply"].startswith("It is the link")
    assert body["report"]["title"] == "Silica link for MIR ATR"  # previous report from MemorySaver
    assert [t["step"] for t in body["trace"]][-1] == "Explain the previous report"
