from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import json
from app.crew.agent_events import (
    EventBus,
    EventType,
    EventDependency,
    event_bus,
    event_dependency,
    create_event
)
from app.crew.error_handler import CircuitBreaker, ErrorType


class AgentHealthCheck:
    """Monitor health of individual agents"""

    def __init__(self):
        self.health_status: Dict[str, Dict[str, Any]] = {}

    def register_agent(self, agent_name: str):
        """Register a new agent"""
        self.health_status[agent_name] = {
            "status": "healthy",
            "last_execution": None,
            "success_count": 0,
            "failure_count": 0,
            "average_execution_time": 0.0,
            "circuit_breaker": CircuitBreaker(),
            "last_health_check": datetime.now(),
        }

    def record_success(self, agent_name: str, execution_time: float):
        """Record successful execution"""
        if agent_name not in self.health_status:
            self.register_agent(agent_name)

        status = self.health_status[agent_name]
        status["success_count"] += 1
        status["last_execution"] = datetime.now()
        status["circuit_breaker"].record_success()

        # Update average execution time
        total_executions = status["success_count"] + status["failure_count"]
        old_avg = status["average_execution_time"]
        status["average_execution_time"] = (
            (old_avg * (total_executions - 1) + execution_time) / total_executions
        )

    def record_failure(self, agent_name: str, error: Exception):
        """Record failed execution"""
        if agent_name not in self.health_status:
            self.register_agent(agent_name)

        status = self.health_status[agent_name]
        status["failure_count"] += 1
        status["last_execution"] = datetime.now()
        status["circuit_breaker"].record_failure()

        if status["circuit_breaker"].is_open():
            status["status"] = "circuit_breaker_open"

    def get_health_status(self, agent_name: str) -> Dict[str, Any]:
        """Get health status of an agent"""
        if agent_name not in self.health_status:
            return {"status": "unknown"}
        return self.health_status[agent_name]

    def is_healthy(self, agent_name: str) -> bool:
        """Check if agent is operational"""
        if agent_name not in self.health_status:
            return True

        status = self.health_status[agent_name]
        circuit_breaker = status.get("circuit_breaker")
        return not circuit_breaker.is_open() if circuit_breaker else True

    def get_all_health_status(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all agents"""
        return {
            agent: {
                "status": status["status"],
                "success_count": status["success_count"],
                "failure_count": status["failure_count"],
                "average_execution_time": status["average_execution_time"],
                "last_execution": status["last_execution"].isoformat()
                if status["last_execution"]
                else None,
            }
            for agent, status in self.health_status.items()
        }


class AgentRegistry:
    """Registry and management of all agents"""

    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.agent_configs: Dict[str, Dict[str, Any]] = {}
        self.health_check = AgentHealthCheck()

    def register(
        self,
        agent_name: str,
        agent_instance: Any,
        config: Optional[Dict[str, Any]] = None,
    ):
        """Register an agent"""
        self.agents[agent_name] = agent_instance
        self.agent_configs[agent_name] = config or {}
        self.health_check.register_agent(agent_name)

    def get_agent(self, agent_name: str) -> Optional[Any]:
        """Get agent instance"""
        return self.agents.get(agent_name)

    def get_all_agents(self) -> Dict[str, Any]:
        """Get all registered agents"""
        return self.agents.copy()

    def is_registered(self, agent_name: str) -> bool:
        """Check if agent is registered"""
        return agent_name in self.agents


class AgentManager:
    """
    Central orchestrator for agent management,
    communication, and execution
    """

    def __init__(self):
        self.registry = AgentRegistry()
        self.event_bus = event_bus
        self.event_dependency = event_dependency
        self.execution_log: List[Dict[str, Any]] = []

    def register_agent(self, agent_name: str, agent_instance: Any, config: Optional[Dict[str, Any]] = None):
        """Register an agent in the system"""
        self.registry.register(agent_name, agent_instance, config)

    def notify_agent_started(
        self,
        agent_name: str,
        source_agent: str,
        target_agents: List[str],
        data: Dict[str, Any],
        correlations_id: str,
    ):
        """Notify that an agent has started execution"""
        event = create_event(
            event_type=EventType.MARKET_ANALYSIS_STARTED
            if "market" in agent_name.lower()
            else EventType.EXECUTION_INITIATED,
            agent_name=agent_name,
            source_agent=source_agent,
            target_agents=target_agents,
            data=data,
            correlations_id=correlations_id,
        )
        self.event_bus.publish(event)

    def notify_agent_completed(
        self,
        agent_name: str,
        source_agent: str,
        result: Any,
        correlations_id: str,
    ):
        """Notify that an agent has completed execution"""
        event = create_event(
            event_type=EventType.MARKET_ANALYSIS_COMPLETED
            if "market" in agent_name.lower()
            else EventType.EXECUTION_COMPLETED,
            agent_name=agent_name,
            source_agent=source_agent,
            target_agents=[],
            data={"result": result},
            correlations_id=correlations_id,
        )
        self.event_bus.publish(event)
        self.event_dependency.mark_complete(agent_name)

    def notify_error(
        self,
        agent_name: str,
        error: Exception,
        error_type: ErrorType,
        correlations_id: str,
    ):
        """Notify that an error occurred in an agent"""
        event = create_event(
            event_type=EventType.ERROR_OCCURRED,
            agent_name=agent_name,
            source_agent=agent_name,
            target_agents=[],
            data={
                "error": str(error),
                "error_type": error_type.value,
            },
            correlations_id=correlations_id,
        )
        self.event_bus.publish(event)

    def add_dependency(self, dependent_agent: str, required_agent: str):
        """Define that one agent depends on another"""
        self.event_dependency.add_dependency(dependent_agent, required_agent)

    def can_execute(self, agent_name: str) -> bool:
        """Check if agent can execute (all dependencies met)"""
        return self.event_dependency.can_execute(agent_name)

    def get_blocking_dependencies(self, agent_name: str) -> List[str]:
        """Get agents blocking execution of another agent"""
        return self.event_dependency.get_blocking_dependencies(agent_name)

    def record_execution(
        self,
        agent_name: str,
        task_name: str,
        success: bool,
        execution_time: float,
        error: Optional[Exception] = None,
        result: Optional[Any] = None,
    ):
        """Log an execution for monitoring"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "task": task_name,
            "success": success,
            "execution_time": execution_time,
            "error": str(error) if error else None,
            "has_result": result is not None,
        }
        self.execution_log.append(log_entry)

        # Update health check
        if success:
            self.registry.health_check.record_success(agent_name, execution_time)
        else:
            self.registry.health_check.record_failure(agent_name, error or Exception("Unknown error"))

    def get_agent_health(self, agent_name: str) -> Dict[str, Any]:
        """Get health status of an agent"""
        return self.registry.health_check.get_health_status(agent_name)

    def get_all_agent_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all agents"""
        return self.registry.health_check.get_all_health_status()

    def is_agent_healthy(self, agent_name: str) -> bool:
        """Check if agent is healthy and can execute"""
        return self.registry.health_check.is_healthy(agent_name)

    def get_execution_summary(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """Get execution summary for agent(s)"""
        if not self.execution_log:
            return {"total_executions": 0}

        logs = self.execution_log
        if agent_name:
            logs = [l for l in logs if l["agent"] == agent_name]

        successful = [l for l in logs if l["success"]]
        failed = [l for l in logs if not l["success"]]

        return {
            "total_executions": len(logs),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(logs) if logs else 0,
            "average_execution_time": (
                sum(l["execution_time"] for l in logs) / len(logs) if logs else 0
            ),
        }

    def get_agent_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "agents": list(self.registry.get_all_agents().keys()),
            "total_agents": len(self.registry.get_all_agents()),
            "healthy_agents": sum(
                1
                for agent in self.registry.get_all_agents().keys()
                if self.is_agent_healthy(agent)
            ),
            "health_summary": self.get_all_agent_health(),
            "execution_summary": self.get_execution_summary(),
        }


# Global agent manager instance
agent_manager = AgentManager()
