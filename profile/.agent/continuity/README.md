# Continuity Store

This directory is the Foundation-owned, owner-keyed store for non-authoritative cross-repository continuity findings.

Each owner repository resolves to one deterministic JSON file created only by `skills/scripts/continuity_findings.py` under explicit current Foundation task authority. Stored findings retain `authority: NONE` and `status: UNVALIDATED_FOR_OWNER`.

The store contains bounded pointers and metadata only. It is not a task queue, evidence dump, scheduler, issue tracker, or cross-repository authority source. A later Architect must explicitly bind the owner repository, fresh-resolve its canonical truth, and revalidate material findings before any separate task or mutation authority can exist.
