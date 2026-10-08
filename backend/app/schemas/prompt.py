"""Prompt schemas: versioned AI prompt templates and content-filter results."""

from pydantic import BaseModel, Field


class PromptTemplate(BaseModel):
    """A versioned prompt template loaded from `app/data/ai_prompts/` (Implementation Guide §11)."""

    version: str
    system_prompt: str
    user_template: str  # may contain {prompt}, {constraints_formatted}, {time_limit}
    instructions: list[str] = Field(default_factory=list)
    humanity_guidance: list[str] = Field(default_factory=list)


class InjectionRisk(BaseModel):
    """Outcome of a prompt-injection scan (Implementation Guide §5.6)."""

    is_injection: bool
    matched_patterns: list[str] = Field(default_factory=list)
