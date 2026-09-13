from app.agent import answer


def test_demo_explains_property_7_with_evidence(monkeypatch):
    monkeypatch.setenv("AGENT_MODE", "demo")
    reply = answer("Why is Property 7 underperforming?")
    assert "Finding" in reply.text and "Evidence" in reply.text and reply.evidence


def test_demo_refuses_destructive_request(monkeypatch):
    monkeypatch.setenv("AGENT_MODE", "demo")
    assert "can't make" in answer("Delete the worst-performing property").text
