from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import deque


class AgentMetrics:
    """
    Track performance and health metrics for individual agents
    """

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.execution_times: deque = deque(maxlen=window_size)
        self.success_count = 0
        self.failure_count = 0
        self.recent_errors: deque = deque(maxlen=10)
        self.last_execution_time = None
        self.first_execution_time = None
        self.uptime_percentage = 100.0

    def record_execution(
        self,
        success: bool,
        execution_time: float,
        error: Optional[Exception] = None,
    ):
        """Record an execution"""
        self.execution_times.append(execution_time)
        self.last_execution_time = datetime.now()

        if self.first_execution_time is None:
            self.first_execution_time = datetime.now()

        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
            if error:
                self.recent_errors.append({"error": str(error), "timestamp": datetime.now()})

        # Update uptime percentage
        total = self.success_count + self.failure_count
        self.uptime_percentage = (self.success_count / total * 100) if total > 0 else 100.0

    def get_average_execution_time(self) -> float:
        """Get average execution time"""
        if not self.execution_times:
            return 0.0
        return sum(self.execution_times) / len(self.execution_times)

    def get_min_execution_time(self) -> float:
        """Get minimum execution time"""
        if not self.execution_times:
            return 0.0
        return min(self.execution_times)

    def get_max_execution_time(self) -> float:
        """Get maximum execution time"""
        if not self.execution_times:
            return 0.0
        return max(self.execution_times)

    def get_success_rate(self) -> float:
        """Get success rate as percentage"""
        total = self.success_count + self.failure_count
        return (self.success_count / total * 100) if total > 0 else 0.0

    def get_health_score(self) -> float:
        """
        Calculate agent health score (0-100)
        Based on success rate, response time, and error trends
        """
        success_rate = self.get_success_rate()
        avg_time = self.get_average_execution_time()

        # Penalize slow responses (assuming 5s is too slow)
        time_score = max(0, 100 - (avg_time / 5.0 * 100)) if avg_time > 0 else 100

        # Combine scores
        health_score = (success_rate * 0.7) + (time_score * 0.3)

        return min(100, max(0, health_score))

    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        return {
            "total_executions": self.success_count + self.failure_count,
            "successful": self.success_count,
            "failed": self.failure_count,
            "success_rate": self.get_success_rate(),
            "average_execution_time": self.get_average_execution_time(),
            "min_execution_time": self.get_min_execution_time(),
            "max_execution_time": self.get_max_execution_time(),
            "uptime_percentage": self.uptime_percentage,
            "health_score": self.get_health_score(),
            "last_execution": self.last_execution_time.isoformat()
            if self.last_execution_time
            else None,
            "recent_errors": [
                {"error": e["error"], "timestamp": e["timestamp"].isoformat()}
                for e in self.recent_errors
            ],
        }

    def is_healthy(self, min_health_score: float = 70.0) -> bool:
        """Check if agent is healthy based on health score"""
        return self.get_health_score() >= min_health_score


class MetricsCollector:
    """
    Collects and manages metrics for all agents
    """

    def __init__(self):
        self.metrics: Dict[str, AgentMetrics] = {}

    def register_agent(self, agent_name: str) -> AgentMetrics:
        """Register a new agent for metrics tracking"""
        if agent_name not in self.metrics:
            self.metrics[agent_name] = AgentMetrics()
        return self.metrics[agent_name]

    def record_execution(
        self,
        agent_name: str,
        success: bool,
        execution_time: float,
        error: Optional[Exception] = None,
    ):
        """Record an execution for an agent"""
        if agent_name not in self.metrics:
            self.register_agent(agent_name)

        self.metrics[agent_name].record_execution(success, execution_time, error)

    def get_metrics(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific agent"""
        if agent_name not in self.metrics:
            return None
        return self.metrics[agent_name].get_summary()

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all agents"""
        return {agent: metrics.get_summary() for agent, metrics in self.metrics.items()}

    def get_healthy_agents(self, min_health_score: float = 70.0) -> Dict[str, float]:
        """Get list of healthy agents with their health scores"""
        return {
            agent: metrics.get_health_score()
            for agent, metrics in self.metrics.items()
            if metrics.is_healthy(min_health_score)
        }

    def get_unhealthy_agents(self, max_health_score: float = 70.0) -> Dict[str, float]:
        """Get list of unhealthy agents with their health scores"""
        return {
            agent: metrics.get_health_score()
            for agent, metrics in self.metrics.items()
            if not metrics.is_healthy(max_health_score)
        }

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health"""
        if not self.metrics:
            return {"total_agents": 0, "system_health_score": 0}

        all_metrics = self.get_all_metrics()
        health_scores = [m["health_score"] for m in all_metrics.values()]

        avg_health = sum(health_scores) / len(health_scores) if health_scores else 0
        success_rates = [m["success_rate"] for m in all_metrics.values()]
        avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0

        return {
            "total_agents": len(self.metrics),
            "healthy_agents": len(self.get_healthy_agents()),
            "unhealthy_agents": len(self.get_unhealthy_agents()),
            "system_health_score": avg_health,
            "overall_success_rate": avg_success_rate,
            "agents": all_metrics,
        }

    def get_performance_report(self) -> str:
        """Generate a formatted performance report"""
        system_health = self.get_system_health()

        report = f"""
╔════════════════════════════════════════════╗
║     AGENT SYSTEM PERFORMANCE REPORT        ║
╚════════════════════════════════════════════╝

System Health Score: {system_health['system_health_score']:.1f}/100
Overall Success Rate: {system_health['overall_success_rate']:.1f}%

Agents: {system_health['total_agents']} total
├─ Healthy: {system_health['healthy_agents']}
└─ Unhealthy: {system_health['unhealthy_agents']}

"""

        for agent_name, metrics in system_health["agents"].items():
            report += f"""
Agent: {agent_name}
├─ Health Score: {metrics['health_score']:.1f}/100
├─ Success Rate: {metrics['success_rate']:.1f}%
├─ Executions: {metrics['total_executions']} ({metrics['successful']} OK, {metrics['failed']} FAIL)
├─ Avg Time: {metrics['average_execution_time']:.3f}s
├─ Uptime: {metrics['uptime_percentage']:.1f}%
"""
            if metrics["recent_errors"]:
                report += f"└─ Recent Errors: {len(metrics['recent_errors'])}\n"

        return report


# Global metrics collector instance
metrics_collector = MetricsCollector()
