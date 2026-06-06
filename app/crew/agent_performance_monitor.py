from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class AgentPerformanceMonitor:
    """
    Monitors agent performance and identifies optimization opportunities
    """

    def __init__(self):
        self.agent_performance: Dict[str, Dict[str, Any]] = {}
        self.performance_history: List[Dict[str, Any]] = []

    def record_performance(
        self,
        agent_name: str,
        task_name: str,
        success: bool,
        execution_time: float,
        quality_score: float = 0.0,
        confidence_level: float = 0.0,
    ):
        """Record performance metrics for an agent"""
        if agent_name not in self.agent_performance:
            self.agent_performance[agent_name] = {
                "tasks": {},
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "average_execution_time": 0.0,
                "average_quality_score": 0.0,
                "average_confidence": 0.0,
            }

        agent_perf = self.agent_performance[agent_name]

        # Initialize task if new
        if task_name not in agent_perf["tasks"]:
            agent_perf["tasks"][task_name] = {
                "executions": 0,
                "successful": 0,
                "failed": 0,
                "avg_time": 0.0,
                "avg_quality": 0.0,
            }

        task_perf = agent_perf["tasks"][task_name]

        # Update counts
        task_perf["executions"] += 1
        agent_perf["total_executions"] += 1

        if success:
            task_perf["successful"] += 1
            agent_perf["successful_executions"] += 1
        else:
            task_perf["failed"] += 1
            agent_perf["failed_executions"] += 1

        # Update averages
        n = task_perf["executions"]
        task_perf["avg_time"] = (task_perf["avg_time"] * (n - 1) + execution_time) / n
        task_perf["avg_quality"] = (
            task_perf["avg_quality"] * (n - 1) + quality_score
        ) / n

        agent_perf["average_execution_time"] = sum(
            t["avg_time"] * t["executions"]
            for t in agent_perf["tasks"].values()
        ) / max(1, agent_perf["total_executions"])

        agent_perf["average_quality_score"] = sum(
            t["avg_quality"] * t["executions"]
            for t in agent_perf["tasks"].values()
        ) / max(1, agent_perf["total_executions"])

        agent_perf["average_confidence"] = confidence_level

        # Store in history
        self.performance_history.append(
            {
                "timestamp": datetime.now(),
                "agent": agent_name,
                "task": task_name,
                "success": success,
                "execution_time": execution_time,
                "quality_score": quality_score,
                "confidence_level": confidence_level,
            }
        )

    def get_agent_performance(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get performance metrics for an agent"""
        return self.agent_performance.get(agent_name)

    def get_all_performance(self) -> Dict[str, Dict[str, Any]]:
        """Get performance for all agents"""
        return self.agent_performance.copy()

    def get_task_performance(self, agent_name: str, task_name: str) -> Optional[Dict[str, Any]]:
        """Get performance for a specific agent-task combination"""
        agent_perf = self.agent_performance.get(agent_name)
        if agent_perf:
            return agent_perf["tasks"].get(task_name)
        return None

    def identify_bottlenecks(self) -> Dict[str, List[str]]:
        """Identify performance bottlenecks"""
        bottlenecks = {
            "slow_agents": [],
            "unreliable_agents": [],
            "low_quality_agents": [],
        }

        for agent_name, perf in self.agent_performance.items():
            # Slow agents (execution time > 2 seconds)
            if perf["average_execution_time"] > 2.0:
                bottlenecks["slow_agents"].append(
                    f"{agent_name} ({perf['average_execution_time']:.2f}s avg)"
                )

            # Unreliable agents (success rate < 90%)
            total = perf["successful_executions"] + perf["failed_executions"]
            if total > 0:
                success_rate = perf["successful_executions"] / total
                if success_rate < 0.9:
                    bottlenecks["unreliable_agents"].append(
                        f"{agent_name} ({success_rate * 100:.1f}% success rate)"
                    )

            # Low quality agents (quality score < 70)
            if perf["average_quality_score"] < 70:
                bottlenecks["low_quality_agents"].append(
                    f"{agent_name} ({perf['average_quality_score']:.1f} quality)"
                )

        return bottlenecks

    def get_optimization_recommendations(self) -> List[str]:
        """Get recommendations for optimization"""
        recommendations = []
        bottlenecks = self.identify_bottlenecks()

        for slow_agent in bottlenecks["slow_agents"]:
            recommendations.append(
                f"Optimize {slow_agent}: Consider caching, parallelization, or algorithm improvement"
            )

        for unreliable_agent in bottlenecks["unreliable_agents"]:
            recommendations.append(
                f"Improve reliability of {unreliable_agent}: Add retry logic or error handling"
            )

        for low_quality_agent in bottlenecks["low_quality_agents"]:
            recommendations.append(
                f"Enhance quality of {low_quality_agent}: Review algorithm and increase validation"
            )

        return recommendations

    def get_comparative_analysis(self) -> Dict[str, Dict[str, float]]:
        """Compare performance across agents"""
        comparison = {}

        # Normalize metrics for comparison
        all_agents = list(self.agent_performance.keys())
        if not all_agents:
            return comparison

        # Get max values for normalization
        max_time = max(
            (a["average_execution_time"] for a in self.agent_performance.values()),
            default=1.0,
        )
        min_time = min(
            (a["average_execution_time"] for a in self.agent_performance.values()),
            default=1.0,
        )

        for agent_name, perf in self.agent_performance.items():
            total = perf["successful_executions"] + perf["failed_executions"]
            success_rate = (
                perf["successful_executions"] / total if total > 0 else 0
            )

            # Speed score (0-100, higher is faster)
            if max_time > min_time:
                speed_score = (
                    (max_time - perf["average_execution_time"]) /
                    (max_time - min_time) * 100
                )
            else:
                speed_score = 100.0

            # Reliability score (success rate * 100)
            reliability_score = success_rate * 100

            # Quality score (already 0-100)
            quality_score = perf["average_quality_score"]

            # Overall score (weighted)
            overall_score = (
                speed_score * 0.2 +
                reliability_score * 0.4 +
                quality_score * 0.4
            )

            comparison[agent_name] = {
                "speed_score": speed_score,
                "reliability_score": reliability_score,
                "quality_score": quality_score,
                "overall_score": overall_score,
            }

        return comparison

    def get_performance_report(self) -> str:
        """Generate a performance report"""
        report = f"""
╔════════════════════════════════════════════╗
║    AGENT PERFORMANCE ANALYSIS REPORT       ║
╚════════════════════════════════════════════╝

"""
        for agent_name, perf in self.agent_performance.items():
            total = perf["successful_executions"] + perf["failed_executions"]
            success_rate = (
                perf["successful_executions"] / total * 100
                if total > 0
                else 0
            )

            report += f"""
Agent: {agent_name}
├─ Total Executions: {total}
├─ Successful: {perf['successful_executions']} ({success_rate:.1f}%)
├─ Failed: {perf['failed_executions']}
├─ Avg Execution Time: {perf['average_execution_time']:.3f}s
├─ Avg Quality Score: {perf['average_quality_score']:.1f}/100
├─ Avg Confidence: {perf['average_confidence']:.1f}%
└─ Tasks:
"""

            for task_name, task_perf in perf["tasks"].items():
                task_success = (
                    task_perf["successful"] / task_perf["executions"] * 100
                    if task_perf["executions"] > 0
                    else 0
                )
                report += f"""   ├─ {task_name}
   │  ├─ Executions: {task_perf['executions']}
   │  ├─ Success Rate: {task_success:.1f}%
   │  ├─ Avg Time: {task_perf['avg_time']:.3f}s
   │  └─ Avg Quality: {task_perf['avg_quality']:.1f}/100
"""

        # Bottlenecks
        bottlenecks = self.identify_bottlenecks()
        if any(bottlenecks.values()):
            report += "\n\n╔════════════════════════════════════════════╗\n"
            report += "║           IDENTIFIED BOTTLENECKS           ║\n"
            report += "╚════════════════════════════════════════════╝\n\n"

            if bottlenecks["slow_agents"]:
                report += "Slow Agents:\n"
                for agent in bottlenecks["slow_agents"]:
                    report += f"  • {agent}\n"

            if bottlenecks["unreliable_agents"]:
                report += "\nUnreliable Agents:\n"
                for agent in bottlenecks["unreliable_agents"]:
                    report += f"  • {agent}\n"

            if bottlenecks["low_quality_agents"]:
                report += "\nLow Quality Agents:\n"
                for agent in bottlenecks["low_quality_agents"]:
                    report += f"  • {agent}\n"

        # Recommendations
        recommendations = self.get_optimization_recommendations()
        if recommendations:
            report += "\n\n╔════════════════════════════════════════════╗\n"
            report += "║      OPTIMIZATION RECOMMENDATIONS          ║\n"
            report += "╚════════════════════════════════════════════╝\n\n"

            for i, rec in enumerate(recommendations, 1):
                report += f"{i}. {rec}\n"

        return report

    def clear_history(self):
        """Clear performance history"""
        self.performance_history.clear()

    def get_recent_history(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get performance history from recent time period"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [
            entry
            for entry in self.performance_history
            if entry["timestamp"] > cutoff_time
        ]


# Global performance monitor instance
agent_performance_monitor = AgentPerformanceMonitor()
