from fastapi import APIRouter

from app.agents.reflection_agent import (
    ReflectionAgent
)
router = APIRouter()

agent = ReflectionAgent()

@router.get("/reflection-analysis")
def reflection_analysis():
    
    result = agent.reflect_on_performance()

    return result