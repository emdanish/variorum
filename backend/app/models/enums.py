from __future__ import annotations

import enum


class IndexingStatus(str, enum.Enum):
    pending = "pending"
    indexing = "indexing"
    indexed = "indexed"
    failed = "failed"


class JobType(str, enum.Enum):
    index = "index"
    pr_analysis = "pr_analysis"


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class JobTrigger(str, enum.Enum):
    webhook = "webhook"
    manual = "manual"


class DocumentKind(str, enum.Enum):
    markdown = "markdown"
    docstring = "docstring"
    comment_block = "comment_block"
    other = "other"


class LinkSource(str, enum.Enum):
    heuristic = "heuristic"
    ai = "ai"


class DriftSeverity(str, enum.Enum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"


class FindingStatus(str, enum.Enum):
    detected = "detected"
    pr_opened = "pr_opened"
    dismissed = "dismissed"
