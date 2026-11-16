from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from ..auth import current_user
from ..agents.copilot import query, POLICY

router = APIRouter(prefix="/api/policy", tags=["policy"])


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=3000)


@router.get("")
def policy(user=Depends(current_user)):
    return POLICY


@router.post("/query")
async def ask(body: Question, user=Depends(current_user)):
    return await query(body.question)
