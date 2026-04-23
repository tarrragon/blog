# Codex Working Rules

This repository treats backend knowledge cards as atomic, service-oriented concepts.

## Core Principle

Do not create a card just because a term appears frequently. Create or split cards only when the term represents a distinct service responsibility, operational behavior, failure mode, or lifecycle boundary.

## Atomic Card Standard

- One card should describe one semantic concept.
- If the same word has multiple meanings across backend scenarios, split it into separate cards.
- Prefer precise, scenario-specific naming over broad umbrella terms.
- Avoid generic cards for words like `runtime`, `channel`, or `gate` unless the meaning is narrow and service-specific.

## When To Split A Card

Split a term into multiple cards when it changes meaning across these axes:

- transport vs. process vs. workflow
- durable vs. ephemeral
- ordered vs. unordered
- replayable vs. one-way
- single consumer vs. fan-out
- human workflow vs. machine protocol
- service boundary vs. language boundary

For example, `channel` can mean different things depending on context:

- in-process channel
- pub/sub channel
- websocket channel
- notification channel
- incident communication channel

Those are not interchangeable. Each one carries different lifecycle, delivery, retry, and observability expectations, so they should become separate cards when the article needs to explain them as distinct backend responsibilities.

## Common Ambiguous Terms

These terms often look singular but usually hide multiple backend responsibilities:

- `channel`: in-process handoff, pub/sub delivery, websocket push path, notification path, incident communication path
- `protocol`: transport framing, queue semantics, handover rules, deployment contracts
- `adapter`: repository adapter, provider adapter, notification adapter, protocol adapter
- `gate`: release gate, cutover gate, admission gate, validation gate
- `endpoint`: public API, admin API, webhook endpoint, diagnostic endpoint, internal endpoint

When one of these appears in an article, prefer the most specific meaning available. If the article needs to explain more than one meaning, split the card instead of overloading a single page.

## Scenario-Driven Writing

Backend articles should expand from the card into concrete usage scenarios:

- what to watch for
- what failure modes matter
- what concurrency or lifecycle issues appear
- what mitigation strategies exist
- how to evaluate the problem completely

For example, `backpressure` is not just a definition. It should lead into the relevant service situations, operational cautions, concurrency concerns, and resolution patterns.

## Editing Rule

When a term is too broad, do not force it into a card. Rewrite it as a specific service context instead.

Examples:

- `sync runtime`
- `async runtime`
- `thread-based runtime`
- `event-loop runtime`
- `container runtime`
- `runtime validation`

These are contextual usage notes, not standalone glossary targets.

## Goal

The purpose of the knowledge-card system is to keep later backend chapters precise. Each card should be accurate enough that subsequent articles can reuse it as a stable conceptual building block.

## Outline As Backlog

Use outlines as the only planning surface for pending work.

- When a card should be split, expanded, or newly added, first update the relevant chapter outline.
- Do not maintain a separate todo list or sidecar checklist for these content decisions.
- The outline should make unfinished work visible by itself, so a quick read shows what still needs to be done.
- If an outline is missing the next step, add that step to the outline before doing the content change.
