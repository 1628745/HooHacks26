from fastapi import APIRouter, HTTPException

from app.models.schemas import ChatRequest, ChatResponse
from app.services.optimizer.llm_prompts import build_chat_prompt
from app.services.optimizer.llm_response_parser import split_explanation_and_code
from app.services.llm.openrouter_client import OpenRouterError, generate_text, openrouter_configured
from app.services.validation.syntax_guard import validate_python_syntax

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat_with_assistant(payload: ChatRequest) -> ChatResponse:
    if not openrouter_configured():
        raise HTTPException(
            status_code=503,
            detail="OpenRouter is not configured. Set OPENROUTER_API_KEY in backend/.env",
        )

    conv_lines: list[str] = []
    for m in payload.messages:
        role = m.role.lower()
        if role == "user":
            conv_lines.append(f"User: {m.content}")
        elif role == "assistant":
            conv_lines.append(f"Assistant: {m.content}")
        else:
            conv_lines.append(f"{m.role}: {m.content}")

    prompt = build_chat_prompt(payload.file_name, payload.current_code, conv_lines)
    try:
        raw = generate_text(prompt)
    except OpenRouterError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    explanation, code = split_explanation_and_code(raw)
    assistant_message = explanation.strip() if explanation else raw.strip()

    if code:
        valid, errors = validate_python_syntax(code)
        if not valid:
            return ChatResponse(
                assistant_message=(
                    assistant_message
                    + "\n\n(Code block present but invalid Python: "
                    + "; ".join(errors)
                    + ")"
                ),
                updated_code=None,
                llm_used=True,
            )
        return ChatResponse(assistant_message=assistant_message, updated_code=code, llm_used=True)

    return ChatResponse(assistant_message=assistant_message, updated_code=None, llm_used=True)
