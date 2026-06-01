from fastapi import APIRouter
from pydantic import BaseModel, Field
from beacon.core.database import DbSession
from beacon.auth.dependencies import CurrentUser

router = APIRouter()


class ChatMessage(BaseModel):
    role: str  # user or assistant
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)
    agent_version_id: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    trace_id: str | None = None
    safety_flagged: bool = False
    review_priority: str | None = None


@router.post("", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> ChatResponse:
    import uuid
    from beacon.models.agent import AgentVersion
    from beacon.integrations.anthropic_client import get_anthropic_client
    from beacon.services.eval import TraceService
    from beacon.schemas.eval import TraceIngest
    from sqlalchemy import select

    # Load agent version
    result = await session.execute(
        select(AgentVersion).where(AgentVersion.id == uuid.UUID(data.agent_version_id))
    )
    agent_version = result.scalar_one_or_none()
    if not agent_version:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Agent version not found")

    # Build messages for Anthropic
    anthropic_messages = [
        {"role": msg.role, "content": msg.content}
        for msg in data.messages
    ]

    # Call the agent
    client = get_anthropic_client()
    agent_result = await client.call_agent(
        system_prompt=agent_version.system_prompt,
        user_message=data.messages[-1].content,
        model=agent_version.model_id,
        max_tokens=agent_version.max_tokens,
        temperature=agent_version.temperature,
        metadata={"session_id": data.session_id, "agent_version_id": data.agent_version_id},
    )

    response_text = agent_result["text"]

    # Ingest as a production trace (runs safety pipeline automatically)
    trace_service = TraceService(session)
    trace_ingest = TraceIngest(
        agent_version_id=uuid.UUID(data.agent_version_id),
        raw_prompt=data.messages[-1].content,
        raw_response=response_text,
        session_id=data.session_id or str(uuid.uuid4()),
        input_tokens=agent_result.get("input_tokens"),
        output_tokens=agent_result.get("output_tokens"),
        model_id=agent_version.model_id,
    )
    trace = await trace_service.ingest(trace_ingest)

    return ChatResponse(
        response=response_text,
        trace_id=str(trace.id),
        safety_flagged=trace.needs_review,
        review_priority=trace.review_priority,
    )
