from fastapi import APIRouter, HTTPException

from app.models import AgentTurnRequest, AgentTurnResponse
from app import leads_store, llm_agent
from app.config import config

router = APIRouter(tags=["Agent"])


# POST /agent/turn
# Gets: JSON body {lead_id?: int, user_utterance: str, history?: list[dict]}
# Returns: AgentTurnResponse {agent_reply: str, action?: str, action_payload?: dict}
# Example:
#   curl -X POST http://localhost:8000/agent/turn \
#     -H 'Content-Type: application/json' \
#     -d '{"lead_id": 1, "user_utterance": "Hello", "history": []}'
@router.post("/agent/turn", response_model=AgentTurnResponse)
async def agent_turn(request: AgentTurnRequest):
    """Process a conversation turn with the AI agent (no telephony)."""

    if not config.has_openai_key():
        raise HTTPException(status_code=503, detail="OpenAI is not configured")

    lead = None
    if request.lead_id:
        lead = leads_store.get_lead_by_id(request.lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail=f"Lead {request.lead_id} not found")

    history = request.history or []

    agent_reply, action, action_payload = llm_agent.decide_next_turn_llm(
        lead=lead,
        history=history,
        last_user_utterance=request.user_utterance,
    )

    return AgentTurnResponse(agent_reply=agent_reply, action=action, action_payload=action_payload)
