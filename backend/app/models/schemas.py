from typing import Optional

from pydantic import BaseModel, Field


class PipelineNode(BaseModel):
    id: str
    label: str
    node_type: str
    code_span: Optional[tuple[int, int]] = None
    metadata: dict = Field(default_factory=dict)
    confidence: float = 0.5
    notes: list[str] = Field(default_factory=list)


class PipelineEdge(BaseModel):
    source: str
    target: str


class PipelineIR(BaseModel):
    nodes: list[PipelineNode]
    edges: list[PipelineEdge]


class Issue(BaseModel):
    id: str
    issue_type: str
    severity: str
    title: str
    description: str
    node_ids: list[str] = Field(default_factory=list)
    suggested_action: str


class Metrics(BaseModel):
    llm_calls: int
    token_estimate: int
    energy_wh: float


class AnalyzeRequest(BaseModel):
    file_name: str
    code: str


class AnalyzeResponse(BaseModel):
    ir: PipelineIR
    issues: list[Issue]
    metrics_before: Metrics
    parser_notes: list[str] = Field(default_factory=list)


class OptimizeRequest(BaseModel):
    file_name: str
    original_code: str
    ir: PipelineIR
    selected_issue_ids: Optional[list[str]] = None


class OptimizeResponse(BaseModel):
    optimized_code: str
    issues_applied: list[str]
    explanation: str
    metrics_before: Metrics
    metrics_after: Metrics
    diff_hunks: list[str]
    llm_used: bool = False


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    file_name: str
    current_code: str
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    assistant_message: str
    updated_code: Optional[str] = None
    llm_used: bool = True


class ValidateRequest(BaseModel):
    code: str


class ValidateResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
