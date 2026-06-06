from dataclasses import dataclass, asdict
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
from datetime import datetime
import json


class EventType(Enum):
    """Event types for agent communication"""
    # Market analysis events
    MARKET_ANALYSIS_STARTED = "market_analysis_started"
    MARKET_ANALYSIS_COMPLETED = "market_analysis_completed"
    MARKET_SETUP_IDENTIFIED = "market_setup_identified"

    # Validation events
    RISK_VALIDATION_STARTED = "risk_validation_started"
    RISK_VALIDATION_COMPLETED = "risk_validation_completed"
    TECHNICAL_VALIDATION_STARTED = "technical_validation_started"
    TECHNICAL_VALIDATION_COMPLETED = "technical_validation_completed"
    SENTIMENT_ANALYSIS_STARTED = "sentiment_analysis_started"
    SENTIMENT_ANALYSIS_COMPLETED = "sentiment_analysis_completed"

    # Execution events
    EXECUTION_INITIATED = "execution_initiated"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"

    # Error events
    ERROR_OCCURRED = "error_occurred"
    RETRY_TRIGGERED = "retry_triggered"
    FALLBACK_ACTIVATED = "fallback_activated"
    CIRCUIT_BREAKER_OPENED = "circuit_breaker_opened"

    # Performance events
    PERFORMANCE_ANALYSIS_STARTED = "performance_analysis_started"
    PERFORMANCE_ANALYSIS_COMPLETED = "performance_analysis_completed"


@dataclass
class AgentEvent:
    """
    Represents an event in the agent system
    """
    event_type: EventType
    agent_name: str
    timestamp: datetime
    data: Dict[str, Any]
    source_agent: str
    target_agents: List[str]
    correlations_id: str  # For tracking related events
    priority: int = 5  # 1-10, higher = more urgent

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "source_agent": self.source_agent,
            "target_agents": self.target_agents,
            "correlations_id": self.correlations_id,
            "priority": self.priority
        }


class EventBus:
    """
    Central event bus for agent-to-agent communication
    """
    def __init__(self):
        self.subscribers: Dict[EventType, List[Callable]] = {}
        self.event_history: List[AgentEvent] = []
        self.max_history_size = 1000

    def subscribe(self, event_type: EventType, callback: Callable):
        """Subscribe to an event type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable):
        """Unsubscribe from an event type"""
        if event_type in self.subscribers:
            self.subscribers[event_type].remove(callback)

    def publish(self, event: AgentEvent):
        """Publish an event to all subscribers"""
        # Store in history
        self._store_event(event)

        # Notify subscribers
        if event.event_type in self.subscribers:
            for callback in self.subscribers[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error in event callback: {e}")

    def _store_event(self, event: AgentEvent):
        """Store event in history with size limit"""
        self.event_history.append(event)
        if len(self.event_history) > self.max_history_size:
            self.event_history.pop(0)

    def get_event_history(
        self,
        agent_name: Optional[str] = None,
        event_type: Optional[EventType] = None,
        limit: int = 100
    ) -> List[AgentEvent]:
        """Retrieve event history with filters"""
        filtered = self.event_history

        if agent_name:
            filtered = [e for e in filtered if e.agent_name == agent_name]

        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]

        return filtered[-limit:]


class EventDependency:
    """
    Track dependencies between agents based on events
    """
    def __init__(self):
        self.dependencies: Dict[str, List[str]] = {}
        self.completion_status: Dict[str, bool] = {}

    def add_dependency(self, dependent_agent: str, required_agent: str):
        """Mark that dependent_agent depends on required_agent"""
        if dependent_agent not in self.dependencies:
            self.dependencies[dependent_agent] = []
        if required_agent not in self.dependencies[dependent_agent]:
            self.dependencies[dependent_agent].append(required_agent)

    def mark_complete(self, agent_name: str):
        """Mark an agent's work as complete"""
        self.completion_status[agent_name] = True

    def mark_incomplete(self, agent_name: str):
        """Mark an agent's work as incomplete"""
        self.completion_status[agent_name] = False

    def can_execute(self, agent_name: str) -> bool:
        """Check if all dependencies are satisfied"""
        if agent_name not in self.dependencies:
            return True

        required = self.dependencies[agent_name]
        for dep in required:
            if not self.completion_status.get(dep, False):
                return False
        return True

    def get_blocking_dependencies(self, agent_name: str) -> List[str]:
        """Get list of dependencies that haven't completed"""
        if agent_name not in self.dependencies:
            return []

        required = self.dependencies[agent_name]
        return [d for d in required if not self.completion_status.get(d, False)]


# Global event bus instance
event_bus = EventBus()
event_dependency = EventDependency()


def create_event(
    event_type: EventType,
    agent_name: str,
    source_agent: str,
    target_agents: List[str],
    data: Dict[str, Any],
    correlations_id: str,
    priority: int = 5
) -> AgentEvent:
    """Factory function to create events"""
    return AgentEvent(
        event_type=event_type,
        agent_name=agent_name,
        timestamp=datetime.now(),
        data=data,
        source_agent=source_agent,
        target_agents=target_agents,
        correlations_id=correlations_id,
        priority=priority
    )
