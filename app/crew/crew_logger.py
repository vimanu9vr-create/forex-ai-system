import logging
import json
from typing import Any, Dict, Optional
from datetime import datetime
from pathlib import Path


class CrewLogger:
    """
    Comprehensive logging system for crew operations
    """

    def __init__(self, log_dir: str = "logs", log_level: int = logging.INFO):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True, parents=True)

        # Configure root logger
        self.root_logger = logging.getLogger("crew_ai")
        self.root_logger.setLevel(log_level)

        # Remove existing handlers to avoid duplicates
        self.root_logger.handlers.clear()

        # Create formatters
        detailed_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        json_formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "logger": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}',
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(detailed_formatter)
        self.root_logger.addHandler(console_handler)

        # File handlers for different components
        self.setup_file_handlers(detailed_formatter)

    def setup_file_handlers(self, formatter):
        """Setup file handlers for different log types"""
        # Execution log
        execution_handler = logging.FileHandler(self.log_dir / "execution.log")
        execution_handler.setLevel(logging.INFO)
        execution_handler.setFormatter(formatter)

        # Error log
        error_handler = logging.FileHandler(self.log_dir / "errors.log")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)

        # Debug log
        debug_handler = logging.FileHandler(self.log_dir / "debug.log")
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(formatter)

        # Agent events log
        events_handler = logging.FileHandler(self.log_dir / "agent_events.log")
        events_handler.setLevel(logging.INFO)
        events_handler.setFormatter(formatter)

        self.root_logger.addHandler(execution_handler)
        self.root_logger.addHandler(error_handler)
        self.root_logger.addHandler(debug_handler)
        self.root_logger.addHandler(events_handler)

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger for a specific component"""
        return logging.getLogger(f"crew_ai.{name}")

    def log_agent_execution(
        self,
        agent_name: str,
        task: str,
        status: str,
        execution_time: float,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ):
        """Log an agent execution"""
        logger = self.get_logger("execution")

        log_data = {
            "agent": agent_name,
            "task": task,
            "status": status,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat(),
        }

        if result:
            log_data["result_keys"] = list(result.keys()) if isinstance(result, dict) else str(type(result))

        if error:
            log_data["error"] = error
            logger.error(json.dumps(log_data, indent=2))
        else:
            logger.info(json.dumps(log_data, indent=2))

    def log_agent_event(
        self,
        event_type: str,
        agent_name: str,
        source_agent: str,
        target_agents: list,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Log an agent event"""
        logger = self.get_logger("agent_events")

        log_data = {
            "event_type": event_type,
            "agent": agent_name,
            "source_agent": source_agent,
            "target_agents": target_agents,
            "timestamp": datetime.now().isoformat(),
        }

        if data:
            log_data["data"] = str(data)[:500]  # Limit data size

        logger.info(json.dumps(log_data, indent=2))

    def log_error(
        self,
        error_type: str,
        agent_name: str,
        error_message: str,
        error_context: Optional[Dict[str, Any]] = None,
    ):
        """Log an error with context"""
        logger = self.get_logger("errors")

        log_data = {
            "error_type": error_type,
            "agent": agent_name,
            "message": error_message,
            "timestamp": datetime.now().isoformat(),
        }

        if error_context:
            log_data["context"] = error_context

        logger.error(json.dumps(log_data, indent=2))

    def log_setup_identified(
        self,
        pair: str,
        signal: str,
        probability: float,
        setup_details: Dict[str, Any],
    ):
        """Log when a trade setup is identified"""
        logger = self.get_logger("execution")

        log_data = {
            "event": "setup_identified",
            "pair": pair,
            "signal": signal,
            "probability": probability,
            "timestamp": datetime.now().isoformat(),
            "details_keys": list(setup_details.keys()) if isinstance(setup_details, dict) else None,
        }

        logger.info(json.dumps(log_data, indent=2))

    def log_trade_executed(
        self,
        trade_id: str,
        pair: str,
        signal: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        execution_context: Optional[Dict[str, Any]] = None,
    ):
        """Log when a trade is executed"""
        logger = self.get_logger("execution")

        log_data = {
            "event": "trade_executed",
            "trade_id": trade_id,
            "pair": pair,
            "signal": signal,
            "entry": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "timestamp": datetime.now().isoformat(),
        }

        if execution_context:
            log_data["context"] = execution_context

        logger.info(json.dumps(log_data, indent=2))

    def log_trade_rejected(
        self,
        pair: str,
        signal: str,
        rejection_reason: str,
        setup_details: Optional[Dict[str, Any]] = None,
    ):
        """Log when a trade is rejected"""
        logger = self.get_logger("execution")

        log_data = {
            "event": "trade_rejected",
            "pair": pair,
            "signal": signal,
            "reason": rejection_reason,
            "timestamp": datetime.now().isoformat(),
        }

        if setup_details:
            log_data["setup_keys"] = list(setup_details.keys()) if isinstance(setup_details, dict) else None

        logger.warning(json.dumps(log_data, indent=2))

    def log_performance_analysis(
        self,
        total_trades: int,
        win_rate: float,
        total_profit_loss: float,
        analysis_details: Optional[Dict[str, Any]] = None,
    ):
        """Log performance analysis results"""
        logger = self.get_logger("execution")

        log_data = {
            "event": "performance_analysis",
            "total_trades": total_trades,
            "win_rate": win_rate,
            "total_profit_loss": total_profit_loss,
            "timestamp": datetime.now().isoformat(),
        }

        if analysis_details:
            log_data["details"] = analysis_details

        logger.info(json.dumps(log_data, indent=2))

    def get_recent_logs(self, log_type: str = "execution", lines: int = 50) -> str:
        """Get recent logs from a file"""
        log_file = self.log_dir / f"{log_type}.log"

        if not log_file.exists():
            return f"No logs found for {log_type}"

        with open(log_file, "r") as f:
            all_lines = f.readlines()
            return "".join(all_lines[-lines:])

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors from error log"""
        error_file = self.log_dir / "errors.log"

        if not error_file.exists():
            return {"total_errors": 0}

        errors_by_agent = {}
        error_types = {}
        total_errors = 0

        with open(error_file, "r") as f:
            for line in f:
                try:
                    log_entry = json.loads(line.split(" - ")[-1]) if " - " in line else {}
                    if "agent" in log_entry:
                        agent = log_entry["agent"]
                        errors_by_agent[agent] = errors_by_agent.get(agent, 0) + 1

                    if "error_type" in log_entry:
                        error_type = log_entry["error_type"]
                        error_types[error_type] = error_types.get(error_type, 0) + 1

                    total_errors += 1
                except:
                    pass

        return {
            "total_errors": total_errors,
            "errors_by_agent": errors_by_agent,
            "error_types": error_types,
        }


# Global logger instance
crew_logger = CrewLogger()
