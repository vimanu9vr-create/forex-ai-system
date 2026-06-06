import traceback
from datetime import datetime

from crewai import Crew

from app.crew.agents import market_analyst_agent, reflection_agent, execution_agent
from app.crew.tasks import (
    market_analysis_task,
    reflection_task,
    execution_task,
    risk_validation_task,
    technical_validation_task,
    sentiment_alignment_task,
)
from app.crew.agent_manager import agent_manager
from app.crew.crew_logger import crew_logger
from app.crew.agent_metrics import metrics_collector
from app.crew.error_handler import retry_with_backoff

# ── Main trading crew ─────────────────────────────────────────────────────
trading_crew = Crew(
    agents=[market_analyst_agent, reflection_agent, execution_agent],
    tasks=[market_analysis_task, reflection_task, execution_task],
    verbose=True,
    tracing=False,  # don't upload runs to crewai.com; show step output locally instead
)


class EnhancedTradingCrew:
    """
    Orchestrated trading crew with health checks, retry logic, and monitoring.
    """

    def __init__(self):
        self.crew = trading_crew
        self.execution_count = 0
        self.success_count = 0
        self.failure_count = 0

    # ── Public entry point ────────────────────────────────────────────────
    def execute_with_orchestration(self) -> dict:
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.execution_count += 1

        crew_logger.log_agent_event(
            event_type="crew_execution_started",
            agent_name="trading_crew",
            source_agent="orchestrator",
            target_agents=["market_analyst", "reflection_analyst", "execution_engine"],
            data={"execution_id": execution_id},
        )

        try:
            result = retry_with_backoff(
                func=self._execute_crew_safely,
                max_retries=2,
                initial_wait=2.0,
            )

            if result.get("success"):
                self.success_count += 1
                crew_logger.log_agent_event(
                    event_type="crew_execution_completed",
                    agent_name="trading_crew",
                    source_agent="orchestrator",
                    target_agents=[],
                    data={"execution_id": execution_id, "status": "success"},
                )
                return {
                    "success": True,
                    "execution_id": execution_id,
                    "result": result["result"],
                    "execution_count": self.execution_count,
                    "success_rate": self.success_count / self.execution_count * 100,
                }
            else:
                self.failure_count += 1
                crew_logger.log_error(
                    error_type="crew_execution_failed",
                    agent_name="trading_crew",
                    error_message=str(result.get("error", "unknown")),
                    error_context={"execution_id": execution_id},
                )
                return {
                    "success": False,
                    "execution_id": execution_id,
                    "error": str(result.get("error")),
                    "error_type": result["error_type"].value if result.get("error_type") else "unknown",
                    "execution_count": self.execution_count,
                    "success_rate": self.success_count / self.execution_count * 100,
                }

        except Exception as e:
            self.failure_count += 1
            crew_logger.log_error(
                error_type="crew_execution_exception",
                agent_name="trading_crew",
                error_message=str(e),
                error_context={"execution_id": execution_id, "traceback": traceback.format_exc()},
            )
            return {
                "success": False,
                "execution_id": execution_id,
                "error": f"Unexpected error: {e}",
                "execution_count": self.execution_count,
                "success_rate": self.success_count / self.execution_count * 100,
            }

    # ── Internal ──────────────────────────────────────────────────────────
    def _execute_crew_safely(self):
        """
        Run crew.kickoff() behind a health gate.

        Raises on failure so retry_with_backoff can retry/classify the error,
        and returns the raw crew result on success. (Previously this swallowed
        the exception and returned a dict, which defeated the retry logic and
        made execute_with_orchestration report success even when the crew failed.)
        """
        unhealthy = [
            name for name in ["market_analyst", "reflection_analyst", "execution_engine"]
            if not agent_manager.is_agent_healthy(name)
        ]
        if unhealthy:
            raise RuntimeError(f"Unhealthy agents detected: {unhealthy}")

        return self.crew.kickoff()

    def get_system_status(self) -> dict:
        return {
            "agent_status": agent_manager.get_agent_status(),
            "metrics": metrics_collector.get_system_health(),
            "execution_stats": {
                "total": self.execution_count,
                "successful": self.success_count,
                "failed": self.failure_count,
                "success_rate": (self.success_count / self.execution_count * 100)
                if self.execution_count > 0 else 0,
            },
        }

    def get_performance_report(self) -> str:
        rate = (self.success_count / self.execution_count * 100) if self.execution_count > 0 else 0
        return (
            f"Executions: {self.execution_count} | "
            f"Success: {self.success_count} | "
            f"Failed: {self.failure_count} | "
            f"Rate: {rate:.1f}%\n"
            + metrics_collector.get_performance_report()
        )


# Global instances
enhanced_crew = EnhancedTradingCrew()
