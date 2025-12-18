"""
Per-AO API Call Logger

Logs all LLM API requests and responses to dedicated log files per AO.
Format: apicall.<mapname>.<missionname>.<ao_number>.<timestamp>.log
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger('batcom.runtime.api_logger')


class AOAPILogger:
    """
    Logs API calls to per-AO log files for debugging and analysis
    """

    def __init__(self, log_dir: str = "@BATCOM"):
        """
        Initialize API logger

        Args:
            log_dir: Directory for API call logs (default: @BATCOM/llm_calls)
        """
        # Create llm_calls subdirectory
        self.log_dir = os.path.join(log_dir, "llm_calls")
        self.current_log_file: Optional[str] = None
        self.current_ao_id: Optional[str] = None
        self.current_map_name: Optional[str] = None
        self.current_mission_name: Optional[str] = None
        self.current_ao_number: Optional[int] = None
        self.call_count = 0
        self.file_created = False

        # Ensure log directory exists with fallback for Linux compatibility
        if not os.path.exists(self.log_dir):
            try:
                os.makedirs(self.log_dir, exist_ok=True)
                logger.info(f'Created API log directory: {self.log_dir}')
            except (OSError, PermissionError) as e:
                # Fallback to simpler path if @BATCOM fails (Linux compatibility)
                logger.warning(f'Failed to create API log directory {self.log_dir}: {e}')
                try:
                    fallback_dir = os.path.join(os.getcwd(), "batcom_logs", "llm_calls")
                    self.log_dir = fallback_dir
                    os.makedirs(self.log_dir, exist_ok=True)
                    logger.info(f'Using fallback API log directory: {self.log_dir}')
                except Exception as fallback_error:
                    # Last resort: temp directory
                    import tempfile
                    self.log_dir = os.path.join(tempfile.gettempdir(), "batcom_logs", "llm_calls")
                    os.makedirs(self.log_dir, exist_ok=True)
                    logger.info(f'Using temp API log directory: {self.log_dir}')

    def start_ao(self, ao_id: str, map_name: str = 'unknown', mission_name: str = 'unknown', ao_number: int = 0):
        """
        Start logging for a new AO (file will be created on first LLM call)

        Args:
            ao_id: AO identifier
            map_name: Map name
            mission_name: Mission name
            ao_number: AO sequence number
        """
        self.current_ao_id = ao_id
        self.current_map_name = map_name or 'unknown'
        self.current_mission_name = mission_name or 'unknown'
        self.current_ao_number = ao_number or 0
        self.call_count = 0
        self.file_created = False
        self.current_log_file = None

        logger.info(f'API logging initialized for AO {ao_id} - file will be created on first LLM call')

    def _create_log_file(self):
        """
        Create the log file with header (called on first LLM call)
        Timestamp reflects when the first LLM call was made
        """
        if self.file_created or not self.current_ao_id:
            return

        # Generate log filename with timestamp of FIRST LLM call
        # Timestamp format: YYYY_MM_DD_HH_MM_SS
        timestamp = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
        filename = f'apicall.{self.current_map_name}.{self.current_mission_name}.{self.current_ao_number}.{timestamp}.log'
        self.current_log_file = os.path.join(self.log_dir, filename)

        # Write header to log file
        try:
            with open(self.current_log_file, 'w', encoding='utf-8') as f:
                f.write('='*80 + '\n')
                f.write(f'API CALL LOG - AO: {self.current_ao_id}\n')
                f.write('='*80 + '\n')
                f.write(f'Map: {self.current_map_name}\n')
                f.write(f'Mission: {self.current_mission_name}\n')
                f.write(f'AO Number: {self.current_ao_number}\n')
                f.write(f'First LLM Call: {datetime.now().isoformat()}\n')
                f.write('='*80 + '\n\n')

            self.file_created = True
            logger.info(f'API log file created on first LLM call: {self.current_log_file}')
        except Exception as e:
            logger.error(f'Failed to create API log file {self.current_log_file}: {e}')
            self.current_log_file = None

    def log_request(
        self,
        cycle: int,
        mission_time: float,
        provider: str,
        model: str,
        request_data: Dict[str, Any],
        cached_context: Optional[str] = None,
        objectives: Optional[list] = None
    ):
        """
        Log an API request with complete RAW data

        Args:
            cycle: Decision cycle number
            mission_time: Mission time
            provider: LLM provider name
            model: Model name
            request_data: Request payload (world state, mission intent, etc.)
            cached_context: Complete cached context string (system prompt + objectives + history)
            objectives: Complete objectives list
        """
        # Create log file on first LLM call if not already created
        if not self.file_created:
            self._create_log_file()

        if not self.current_log_file:
            return

        self.call_count += 1
        timestamp = datetime.now().isoformat()

        try:
            with open(self.current_log_file, 'a', encoding='utf-8') as f:
                f.write('\n' + '='*80 + '\n')
                f.write(f'API CALL #{self.call_count} - REQUEST\n')
                f.write('='*80 + '\n')
                f.write(f'Timestamp: {timestamp}\n')
                f.write(f'Cycle: {cycle}\n')
                f.write(f'Mission Time: {mission_time:.1f}s\n')
                f.write(f'Provider: {provider}\n')
                f.write(f'Model: {model}\n')
                f.write('-'*80 + '\n')

                # Log complete cached context (NOT truncated)
                if cached_context:
                    f.write('CACHED CONTEXT (COMPLETE RAW DATA):\n')
                    f.write(cached_context)
                    f.write('\n' + '-'*80 + '\n')

                # Log complete objectives (NOT truncated)
                if objectives:
                    f.write('OBJECTIVES (COMPLETE RAW DATA):\n')
                    f.write(json.dumps(objectives, indent=2, ensure_ascii=False))
                    f.write('\n' + '-'*80 + '\n')

                # Log request data (world state, mission intent, etc.)
                f.write('REQUEST DATA (COMPLETE RAW DATA):\n')
                f.write(json.dumps(request_data, indent=2, ensure_ascii=False))
                f.write('\n' + '-'*80 + '\n\n')

        except Exception as e:
            logger.error(f'Failed to log API request: {e}')

    def log_response(
        self,
        success: bool,
        response_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        token_usage: Optional[Dict[str, int]] = None,
        latency_ms: Optional[float] = None,
        raw_response: Optional[str] = None
    ):
        """
        Log an API response with complete RAW data

        Args:
            success: Whether call succeeded
            response_data: Response payload (orders, commentary, etc.)
            error: Error message if failed
            token_usage: Token usage statistics
            latency_ms: Call latency in milliseconds
            raw_response: Complete raw response text from LLM (NOT truncated)
        """
        if not self.current_log_file:
            return

        timestamp = datetime.now().isoformat()

        try:
            with open(self.current_log_file, 'a', encoding='utf-8') as f:
                f.write('RESPONSE:\n')
                f.write(f'Timestamp: {timestamp}\n')
                f.write(f'Success: {success}\n')

                if latency_ms is not None:
                    f.write(f'Latency: {latency_ms:.1f}ms\n')

                if token_usage:
                    f.write('Token Usage:\n')
                    for key, value in token_usage.items():
                        f.write(f'  {key}: {value}\n')

                # Log complete RAW response from LLM (NOT truncated)
                if raw_response:
                    f.write('-'*80 + '\n')
                    f.write('RAW LLM RESPONSE (COMPLETE, NOT TRUNCATED):\n')
                    f.write(raw_response)
                    f.write('\n' + '-'*80 + '\n')

                # Log parsed response data
                if success and response_data:
                    f.write('PARSED RESPONSE DATA:\n')
                    f.write(json.dumps(response_data, indent=2, ensure_ascii=False))
                    f.write('\n' + '-'*80 + '\n')

                if error:
                    f.write('ERROR:\n')
                    f.write(f'{error}\n')
                    f.write('-'*80 + '\n')

                f.write('='*80 + '\n\n')

        except Exception as e:
            logger.error(f'Failed to log API response: {e}')

    def end_ao(self):
        """End logging for current AO"""
        if self.file_created and self.current_log_file:
            try:
                with open(self.current_log_file, 'a', encoding='utf-8') as f:
                    f.write('\n' + '='*80 + '\n')
                    f.write('API CALL LOG COMPLETED\n')
                    f.write('='*80 + '\n')
                    f.write(f'Total API Calls: {self.call_count}\n')
                    f.write(f'Ended: {datetime.now().isoformat()}\n')
                    f.write('='*80 + '\n')

                logger.info(f'API logging ended for AO {self.current_ao_id}: {self.call_count} calls logged')
            except Exception as e:
                logger.error(f'Failed to finalize API log: {e}')

        self.current_log_file = None
        self.current_ao_id = None
        self.current_map_name = None
        self.current_mission_name = None
        self.current_ao_number = None
        self.call_count = 0
        self.file_created = False

    def get_log_file_path(self) -> Optional[str]:
        """Get current log file path"""
        return self.current_log_file
