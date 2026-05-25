from pydantic import BaseModel, Field


class ClaudeKeyRequest(BaseModel):
    claude_api_key: str = Field(min_length=10, max_length=500)


class OnboardingStatus(BaseModel):
    etsy_connected: bool
    claude_key_added: bool
    complete: bool
