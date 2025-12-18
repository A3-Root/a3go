"""
Command queue - batches and manages commands for SQF execution
"""

import logging
from typing import List, Dict, Any
from collections import deque
from ..models.commands import Command

logger = logging.getLogger('batcom.commands.queue')


class CommandQueue:
    """
    Manages a queue of commands to be executed by SQF

    Handles batching, rate limiting, and command prioritization
    """

    def __init__(self, max_commands_per_batch: int = 30):
        """
        Initialize command queue

        Args:
            max_commands_per_batch: Maximum commands to send in one batch
        """
        self.queue = deque()
        self.max_commands_per_batch = max_commands_per_batch
        self.total_enqueued = 0
        self.total_dequeued = 0

    def enqueue(self, command: Command):
        """
        Add a command to the queue

        Args:
            command: Command to enqueue
        """
        self.queue.append(command)
        self.total_enqueued += 1
        logger.debug('Command enqueued: %s for %s', command.type, command.group_id)

    def enqueue_batch(self, commands: List[Command]):
        """
        Add multiple commands to the queue

        Args:
            commands: List of commands to enqueue
        """
        for cmd in commands:
            self.queue.append(cmd)
        self.total_enqueued += len(commands)
        logger.info('Batch of %d commands enqueued', len(commands))

    def get_batch(self, max_count: int = None) -> List[Dict[str, Any]]:
        """
        Get a batch of commands for SQF execution

        Args:
            max_count: Maximum number of commands to return (uses queue max if None)

        Returns:
            List of command dictionaries
        """
        if max_count is None:
            max_count = self.max_commands_per_batch

        batch = []
        count = min(max_count, len(self.queue))

        for _ in range(count):
            if len(self.queue) == 0:
                break

            cmd = self.queue.popleft()
            batch.append(cmd.to_dict())
            self.total_dequeued += 1

        if len(batch) > 0:
            logger.debug('Returning batch of %d commands', len(batch))

        return batch

    def clear(self):
        """Clear all pending commands"""
        cleared = len(self.queue)
        self.queue.clear()
        if cleared > 0:
            logger.info('Cleared %d pending commands', cleared)

    def size(self) -> int:
        """Get number of pending commands"""
        return len(self.queue)

    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return len(self.queue) == 0

    def stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        return {
            "pending": len(self.queue),
            "total_enqueued": self.total_enqueued,
            "total_dequeued": self.total_dequeued
        }
