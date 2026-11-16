from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from ..auth import current_user
from ..agents.copilot import query, POLICY
from typing import Literal

router = APIRouter(prefix="/api/policy", tags=["policy"])


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=3000)


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=3000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=6)


@router.get("")
def policy(user=Depends(current_user)):
    return POLICY


@router.post("/query")
async def ask(body: Question, user=Depends(current_user)):
    return await query(body.question, [item.model_dump() for item in body.history])
