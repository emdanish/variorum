from __future__ import annotations

import enum


class IndexingStatus(enum.StrEnum):
    pending = "pending"
    indexing = "indexing"
    indexed = "indexed"
    failed = "failed"


class JobType(enum.StrEnum):
    indexing = "indexing"
    pr_analysis = "pr_analysis"


class JobStatus(enum.StrEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class JobTrigger(enum.StrEnum):
    webhook = "webhook"
    manual = "manual"


class DocumentKind(enum.StrEnum):
    markdown = "markdown"
    docstring = "docstring"
    comment_block = "comment_block"
    other = "other"


class LinkSource(enum.StrEnum):
    heuristic = "heuristic"
    ai = "ai"


class DriftSeverity(enum.StrEnum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"


class FindingStatus(enum.StrEnum):
    detected = "detected"
    pr_opened = "pr_opened"
    dismissed = "dismissed"


class KnowledgeKind(enum.StrEnum):
    commit = "commit"
    pull_request = "pull_request"
    issue = "issue"
    review = "review"
