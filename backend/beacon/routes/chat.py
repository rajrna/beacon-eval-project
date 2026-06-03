from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from beacon.core.database import DbSession
from beacon.auth.dependencies import CurrentUser

router = APIRouter()

# Rate limiting config
MAX_MESSAGES_PER_SESSION = 50
MAX_MESSAGE_LENGTH = 2000


class ChatMessage(BaseModel):
    role: str
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
    injection_blocked: bool = False
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


@router.post("", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> ChatResponse:
    import uuid
    import structlog
    from beacon.models.agent import AgentVersion
    from beacon.integrations.anthropic_client import call_agent
    from beacon.integrations.langfuse_client import get_langfuse_client
    from beacon.services.eval import TraceService
    from beacon.schemas.eval import TraceIngest
    from beacon.safety.injection import check_injection, sanitize_for_prompt
    from sqlalchemy import select

    logger = structlog.get_logger(__name__)

    # ── Rate limiting ─────────────────────────────────────────────────────────
    if len(data.messages) > MAX_MESSAGES_PER_SESSION:
        raise HTTPException(
            status_code=429,
            detail=f"Session limit reached. Maximum {MAX_MESSAGES_PER_SESSION} messages per session.",
        )

    user_message = data.messages[-1].content

    if len(user_message) > MAX_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Message too long. Maximum {MAX_MESSAGE_LENGTH} characters.",
        )

    # ── Load agent version ────────────────────────────────────────────────────
    result = await session.execute(
        select(AgentVersion).where(AgentVersion.id == uuid.UUID(data.agent_version_id))
    )
    agent_version = result.scalar_one_or_none()
    if not agent_version:
        raise HTTPException(status_code=404, detail="Agent version not found")

    # ── Injection check ───────────────────────────────────────────────────────
    injection = check_injection(user_message)

    if injection.blocked:
        logger.warning(
            "injection_blocked",
            pattern=injection.pattern_matched,
            session_id=data.session_id,
        )
        trace_service = TraceService(session)
        trace = await trace_service.ingest(TraceIngest(
            agent_version_id=uuid.UUID(data.agent_version_id),
            raw_prompt=user_message,
            raw_response=injection.safe_response,
            session_id=data.session_id or str(uuid.uuid4()),
            model_id=agent_version.model_id,
        ))
        return ChatResponse(
            response=injection.safe_response,
            trace_id=str(trace.id),
            safety_flagged=True,
            review_priority="concerning",
            injection_blocked=True,
        )

    if injection.flagged:
        logger.info(
            "injection_flagged_soft",
            pattern=injection.pattern_matched,
            session_id=data.session_id,
        )

    # ── Sanitize input ────────────────────────────────────────────────────────
    sanitized_message = sanitize_for_prompt(user_message)

    # ── Build conversation history (all turns except the last) ───────────────
    conversation_history = [
        {"role": m.role, "content": m.content}
        for m in data.messages[:-1]
        if m.role in ("user", "assistant")
    ]

    # ── Call agent with full conversation context ─────────────────────────────
    agent_result = await call_agent(
        system_prompt=agent_version.system_prompt,
        user_message=sanitized_message,
        model=agent_version.model_id,
        max_tokens=agent_version.max_tokens or 1024,
        temperature=agent_version.temperature or 0.0,
        conversation_history=conversation_history,
    )
    response_text = agent_result["text"]

    # ── Ingest trace (runs safety pipeline) ───────────────────────────────────
    trace_service = TraceService(session)
    trace_ingest = TraceIngest(
        agent_version_id=uuid.UUID(data.agent_version_id),
        raw_prompt=user_message,
        raw_response=response_text,
        session_id=data.session_id or str(uuid.uuid4()),
        input_tokens=agent_result.get("input_tokens"),
        output_tokens=agent_result.get("output_tokens"),
        model_id=agent_version.model_id,
    )
    trace = await trace_service.ingest(trace_ingest)

    # Merge injection flag into safety flags
    if injection.flagged and not trace.needs_review:
        trace.needs_review = True
        trace.review_priority = "concerning"
        trace.safety_flags = list(trace.safety_flags or []) + ["injection_attempt"]
        await session.flush()

    # ── Log to Langfuse ───────────────────────────────────────────────────────
    langfuse = get_langfuse_client()
    langfuse.log_chat(
        session_id=data.session_id or str(trace.id),
        agent_version_id=data.agent_version_id,
        user_message=sanitized_message,
        response_text=response_text,
        model=agent_version.model_id,
        input_tokens=agent_result.get("input_tokens", 0),
        output_tokens=agent_result.get("output_tokens", 0),
        safety_flagged=trace.needs_review,
        injection_flagged=injection.flagged,
    )

    return ChatResponse(
        response=response_text,
        trace_id=str(trace.id),
        safety_flagged=trace.needs_review,
        review_priority=trace.review_priority,
        injection_blocked=False,
        input_tokens=agent_result.get("input_tokens", 0),
        output_tokens=agent_result.get("output_tokens", 0),
        cost_usd=agent_result.get("cost_usd", 0.0),
    )