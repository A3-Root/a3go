"""
Token usage tracking and reporting

Tracks LLM token usage with detailed statistics:
- Per call
- Per minute
- Per hour
- Per day
- Total cumulative
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

logger = logging.getLogger('batcom.runtime.token_tracker')


class TokenTracker:
    """
    Tracks token usage statistics and writes to log file
    """

    def __init__(self, log_dir: str = "@BATCOM"):
        """
        Initialize token tracker

        Args:
            log_dir: Directory for token usage logs
        """
        # Ensure log directory exists with fallback for Linux compatibility
        self.log_dir = log_dir
        try:
            os.makedirs(log_dir, exist_ok=True)
        except (OSError, PermissionError) as e:
            # Fallback to simpler path if @BATCOM fails (Linux compatibility)
            logger.warning(f'Failed to create token log directory {log_dir}: {e}')
            try:
                fallback_dir = os.path.join(os.getcwd(), "batcom_logs")
                self.log_dir = fallback_dir
                os.makedirs(self.log_dir, exist_ok=True)
                logger.info(f'Using fallback token log directory: {self.log_dir}')
            except Exception as fallback_error:
                # Last resort: temp directory
                import tempfile
                self.log_dir = os.path.join(tempfile.gettempdir(), "batcom_logs")
                os.makedirs(self.log_dir, exist_ok=True)
                logger.info(f'Using temp token log directory: {self.log_dir}')

        # Log file path
        self.log_file = os.path.join(self.log_dir, "token_usage.jsonl")

        # Cumulative totals
        self.total_calls = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

        # Time-based buckets (timestamp -> stats)
        self.calls_log: List[Dict[str, Any]] = []

        # Start time
        self.start_time = datetime.now()

        logger.info("Token tracker initialized (log file: %s)", self.log_file)

    def record_call(self, input_tokens: int, output_tokens: int, provider: str = "unknown"):
        """
        Record a single LLM API call

        Args:
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated
            provider: LLM provider name
        """
        timestamp = datetime.now()

        # Update cumulative totals
        self.total_calls += 1
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        # Create call record
        call_record = {
            "timestamp": timestamp.isoformat(),
            "call_number": self.total_calls,
            "provider": provider,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cumulative_input": self.total_input_tokens,
            "cumulative_output": self.total_output_tokens,
            "cumulative_total": self.total_input_tokens + self.total_output_tokens
        }

        # Add to log
        self.calls_log.append(call_record)

        # Write to file (append mode, one JSON object per line)
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(call_record) + '\n')
        except Exception as e:
            logger.error("Failed to write token usage to file: %s", e)

        logger.debug("Token usage recorded: call #%d, %d input, %d output",
                    self.total_calls, input_tokens, output_tokens)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive token usage statistics

        Returns:
            Dictionary with detailed statistics
        """
        now = datetime.now()

        # Calculate time periods
        one_minute_ago = now - timedelta(minutes=1)
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)

        # Filter calls by time period
        calls_last_minute = [c for c in self.calls_log
                            if datetime.fromisoformat(c['timestamp']) >= one_minute_ago]
        calls_last_hour = [c for c in self.calls_log
                          if datetime.fromisoformat(c['timestamp']) >= one_hour_ago]
        calls_last_day = [c for c in self.calls_log
                         if datetime.fromisoformat(c['timestamp']) >= one_day_ago]

        # Calculate statistics
        def calc_stats(calls):
            if not calls:
                return {"calls": 0, "input": 0, "output": 0, "total": 0}
            return {
                "calls": len(calls),
                "input": sum(c['input_tokens'] for c in calls),
                "output": sum(c['output_tokens'] for c in calls),
                "total": sum(c['total_tokens'] for c in calls)
            }

        # Last call stats
        last_call = self.calls_log[-1] if self.calls_log else None
        last_call_stats = {
            "input": last_call['input_tokens'] if last_call else 0,
            "output": last_call['output_tokens'] if last_call else 0,
            "total": last_call['total_tokens'] if last_call else 0,
            "timestamp": last_call['timestamp'] if last_call else None
        } if last_call else None

        # Build stats dictionary
        stats = {
            "last_call": last_call_stats,
            "per_minute": calc_stats(calls_last_minute),
            "per_hour": calc_stats(calls_last_hour),
            "per_day": calc_stats(calls_last_day),
            "total": {
                "calls": self.total_calls,
                "input": self.total_input_tokens,
                "output": self.total_output_tokens,
                "total": self.total_input_tokens + self.total_output_tokens
            },
            "averages": {
                "input_per_call": self.total_input_tokens / self.total_calls if self.total_calls > 0 else 0,
                "output_per_call": self.total_output_tokens / self.total_calls if self.total_calls > 0 else 0,
                "total_per_call": (self.total_input_tokens + self.total_output_tokens) / self.total_calls if self.total_calls > 0 else 0
            },
            "session": {
                "start_time": self.start_time.isoformat(),
                "duration_seconds": (now - self.start_time).total_seconds()
            }
        }

        return stats

    def get_stats_formatted(self) -> str:
        """
        Get formatted statistics as a readable string

        Returns:
            Formatted statistics string
        """
        stats = self.get_stats()

        lines = []
        lines.append("=" * 80)
        lines.append("TOKEN USAGE STATISTICS")
        lines.append("=" * 80)

        # Last call
        if stats['last_call']:
            lines.append("")
            lines.append("LAST CALL:")
            lines.append(f"  Time: {stats['last_call']['timestamp']}")
            lines.append(f"  Input tokens: {stats['last_call']['input']}")
            lines.append(f"  Output tokens: {stats['last_call']['output']}")
            lines.append(f"  Total tokens: {stats['last_call']['total']}")

        # Per minute
        lines.append("")
        lines.append("LAST MINUTE:")
        lines.append(f"  Calls: {stats['per_minute']['calls']}")
        lines.append(f"  Input tokens: {stats['per_minute']['input']}")
        lines.append(f"  Output tokens: {stats['per_minute']['output']}")
        lines.append(f"  Total tokens: {stats['per_minute']['total']}")

        # Per hour
        lines.append("")
        lines.append("LAST HOUR:")
        lines.append(f"  Calls: {stats['per_hour']['calls']}")
        lines.append(f"  Input tokens: {stats['per_hour']['input']}")
        lines.append(f"  Output tokens: {stats['per_hour']['output']}")
        lines.append(f"  Total tokens: {stats['per_hour']['total']}")

        # Per day
        lines.append("")
        lines.append("LAST 24 HOURS:")
        lines.append(f"  Calls: {stats['per_day']['calls']}")
        lines.append(f"  Input tokens: {stats['per_day']['input']}")
        lines.append(f"  Output tokens: {stats['per_day']['output']}")
        lines.append(f"  Total tokens: {stats['per_day']['total']}")

        # Total
        lines.append("")
        lines.append("TOTAL (ALL TIME):")
        lines.append(f"  Calls: {stats['total']['calls']}")
        lines.append(f"  Input tokens: {stats['total']['input']}")
        lines.append(f"  Output tokens: {stats['total']['output']}")
        lines.append(f"  Total tokens: {stats['total']['total']}")

        # Averages
        lines.append("")
        lines.append("AVERAGES (PER CALL):")
        lines.append(f"  Input tokens: {stats['averages']['input_per_call']:.1f}")
        lines.append(f"  Output tokens: {stats['averages']['output_per_call']:.1f}")
        lines.append(f"  Total tokens: {stats['averages']['total_per_call']:.1f}")

        # Session info
        duration_hours = stats['session']['duration_seconds'] / 3600
        lines.append("")
        lines.append("SESSION INFO:")
        lines.append(f"  Start time: {stats['session']['start_time']}")
        lines.append(f"  Duration: {duration_hours:.2f} hours ({stats['session']['duration_seconds']:.0f} seconds)")

        lines.append("=" * 80)

        return "\n".join(lines)

    def reset(self):
        """Reset all statistics"""
        self.total_calls = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.calls_log = []
        self.start_time = datetime.now()
        logger.info("Token tracker statistics reset")
