import pytest
import uuid
from app.agent.loop import AgentLoop

@pytest.mark.asyncio
async def test_loop_detection_fingerprint():
    run_id = str(uuid.uuid4())
    loop = AgentLoop(
        run_id=run_id,
        role_id="recruiter",
        task="Test loop detection"
    )

    tool_name = "web_open"
    args = {"url": "/sandbox/ats/jobs/1"}
    page_url = "http://localhost:8000/sandbox/ats/jobs/1"

    # Hash fingerprints
    fp1 = loop._hash_action(tool_name, args, page_url)
    fp2 = loop._hash_action(tool_name, args, page_url)
    assert fp1 == fp2

    loop.action_fingerprints.append(fp1)
    loop.action_fingerprints.append(fp1)
    assert loop.action_fingerprints.count(fp1) == 2
    assert loop.loop_warning_issued is False

    # Third repetition
    loop.action_fingerprints.append(fp1)
    assert loop.action_fingerprints.count(fp1) == 3
