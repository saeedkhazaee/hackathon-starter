"""Finite processing budgets shared by every stage."""
import threading
import time

MAX_ATTEMPTS = 12
MAX_ROWS = 50_000
MAX_PAGES = 100
JOB_SECONDS = 90
MAX_STAGE_OPERATIONS = 15_000


class ProcessingError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class PermanentError(ProcessingError):
    pass


class TransientError(ProcessingError):
    pass


class Stopped(ProcessingError):
    pass


class Budget:
    def __init__(self, cancel=None, seconds=JOB_SECONDS):
        self.cancel = cancel or threading.Event()
        self.deadline = time.monotonic() + seconds
        self.operations = 0

    def check(self):
        if self.cancel.is_set():
            raise Stopped("cancelled", "Processing cancelled")
        if time.monotonic() >= self.deadline:
            raise Stopped("deadline_exceeded", "Job exceeded its processing deadline")

    def stage(self):
        self.check()
        self.operations += 1
        if self.operations > MAX_STAGE_OPERATIONS:
            raise Stopped("operation_limit", "Job exceeded its stage-operation budget")

    def remaining(self):
        self.check()
        return max(0.01, self.deadline - time.monotonic())
