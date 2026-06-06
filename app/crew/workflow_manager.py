from typing import Dict, Any, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid
from datetime import datetime
from dataclasses import dataclass


@dataclass
class WorkflowTask:
    """Represents a single task in the workflow"""
    task_id: str
    task_name: str
    agent_name: str
    func: Callable
    args: tuple
    kwargs: Dict[str, Any]
    parallel: bool = False
    depends_on: List[str] = None

    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []


@dataclass
class WorkflowResult:
    """Result of a single task execution"""
    task_id: str
    task_name: str
    agent_name: str
    success: bool
    result: Any
    error: Optional[Exception]
    execution_time: float
    timestamp: datetime


class WorkflowManager:
    """
    Orchestrates execution of agent workflows with support for
    parallel execution, dependency management, and error recovery
    """

    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self.tasks: Dict[str, WorkflowTask] = {}
        self.results: Dict[str, WorkflowResult] = {}
        self.execution_history: List[WorkflowResult] = []

    def add_task(
        self,
        agent_name: str,
        task_name: str,
        func: Callable,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        parallel: bool = False,
        depends_on: Optional[List[str]] = None,
    ) -> str:
        """Add a task to the workflow"""
        task_id = f"{agent_name}_{task_name}_{uuid.uuid4().hex[:8]}"
        task = WorkflowTask(
            task_id=task_id,
            task_name=task_name,
            agent_name=agent_name,
            func=func,
            args=args,
            kwargs=kwargs or {},
            parallel=parallel,
            depends_on=depends_on or [],
        )
        self.tasks[task_id] = task
        return task_id

    def _execute_task(self, task: WorkflowTask) -> WorkflowResult:
        """Execute a single task"""
        import time

        start_time = time.time()

        try:
            result = task.func(*task.args, **task.kwargs)
            execution_time = time.time() - start_time

            return WorkflowResult(
                task_id=task.task_id,
                task_name=task.task_name,
                agent_name=task.agent_name,
                success=True,
                result=result,
                error=None,
                execution_time=execution_time,
                timestamp=datetime.now(),
            )

        except Exception as e:
            execution_time = time.time() - start_time

            return WorkflowResult(
                task_id=task.task_id,
                task_name=task.task_name,
                agent_name=task.agent_name,
                success=False,
                result=None,
                error=e,
                execution_time=execution_time,
                timestamp=datetime.now(),
            )

    def _get_executable_tasks(self, remaining_tasks: Dict[str, WorkflowTask]) -> List[str]:
        """Get tasks that can be executed now (dependencies satisfied)"""
        from app.crew.agent_manager import agent_manager

        executable = []

        for task_id, task in remaining_tasks.items():
            # Check if all dependencies are completed
            all_dependencies_done = all(
                dep_id in self.results for dep_id in task.depends_on
            )

            # Check if all dependencies succeeded
            all_dependencies_succeeded = all(
                self.results[dep_id].success for dep_id in task.depends_on
            )

            # Check if agent is healthy
            agent_healthy = agent_manager.is_agent_healthy(task.agent_name)

            if all_dependencies_done and all_dependencies_succeeded and agent_healthy:
                executable.append(task_id)

        return executable

    def execute(self, parallel: bool = True) -> Dict[str, Any]:
        """
        Execute all tasks in the workflow

        Args:
            parallel: Whether to execute independent tasks in parallel

        Returns:
            Workflow execution summary
        """
        if not self.tasks:
            return {"success": False, "reason": "No tasks to execute"}

        remaining_tasks = self.tasks.copy()
        self.results.clear()

        while remaining_tasks:
            # Get tasks that can execute now
            executable_task_ids = self._get_executable_tasks(remaining_tasks)

            if not executable_task_ids:
                # Check for circular dependencies or all dependencies failed
                return {
                    "success": False,
                    "reason": "Circular dependency or failed dependencies",
                    "completed": len(self.results),
                    "total": len(self.tasks),
                }

            # Execute tasks (parallel or sequential)
            if parallel and len(executable_task_ids) > 1:
                self._execute_parallel(executable_task_ids, remaining_tasks)
            else:
                self._execute_sequential(executable_task_ids[0], remaining_tasks)

            # Remove executed tasks
            for task_id in executable_task_ids:
                del remaining_tasks[task_id]

        # Store in history
        self.execution_history.extend(self.results.values())

        return self._get_summary()

    def _execute_parallel(self, task_ids: List[str], remaining_tasks: Dict[str, WorkflowTask]):
        """Execute multiple tasks in parallel"""
        tasks_to_execute = [remaining_tasks[tid] for tid in task_ids]

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task_id = {
                executor.submit(self._execute_task, task): task.task_id
                for task in tasks_to_execute
            }

            for future in as_completed(future_to_task_id):
                task_id = future_to_task_id[future]
                try:
                    result = future.result()
                    self.results[task_id] = result
                except Exception as e:
                    self.results[task_id] = WorkflowResult(
                        task_id=task_id,
                        task_name=remaining_tasks[task_id].task_name,
                        agent_name=remaining_tasks[task_id].agent_name,
                        success=False,
                        result=None,
                        error=e,
                        execution_time=0,
                        timestamp=datetime.now(),
                    )

    def _execute_sequential(self, task_id: str, remaining_tasks: Dict[str, WorkflowTask]):
        """Execute a single task sequentially"""
        task = remaining_tasks[task_id]
        result = self._execute_task(task)
        self.results[task_id] = result

    def _get_summary(self) -> Dict[str, Any]:
        """Get workflow execution summary"""
        successful = [r for r in self.results.values() if r.success]
        failed = [r for r in self.results.values() if not r.success]

        total_time = sum(r.execution_time for r in self.results.values())

        return {
            "success": len(failed) == 0,
            "total_tasks": len(self.results),
            "successful_tasks": len(successful),
            "failed_tasks": len(failed),
            "success_rate": len(successful) / len(self.results) if self.results else 0,
            "total_execution_time": total_time,
            "failed_tasks_detail": [
                {
                    "task_id": r.task_id,
                    "agent": r.agent_name,
                    "error": str(r.error),
                }
                for r in failed
            ],
        }

    def get_result(self, task_id: str) -> Optional[WorkflowResult]:
        """Get result of a specific task"""
        return self.results.get(task_id)

    def get_all_results(self) -> Dict[str, WorkflowResult]:
        """Get all task results"""
        return self.results.copy()

    def get_agent_results(self, agent_name: str) -> List[WorkflowResult]:
        """Get all results for a specific agent"""
        return [r for r in self.results.values() if r.agent_name == agent_name]

    def clear(self):
        """Clear all tasks and results"""
        self.tasks.clear()
        self.results.clear()

    def get_execution_history(self, limit: int = 100) -> List[WorkflowResult]:
        """Get recent execution history"""
        return self.execution_history[-limit:]


# Global workflow manager instance
workflow_manager = WorkflowManager()
