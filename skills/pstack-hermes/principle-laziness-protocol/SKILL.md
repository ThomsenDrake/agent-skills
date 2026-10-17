---
name: principle-laziness-protocol
description: "Use when refactoring or tempted to add abstractions."
compatibility: Hermes Agent; repository file tools and terminal for checks.
---

# Laziness Protocol

When refactoring, evaluating diff size, or tempted to add abstractions, layers, or signal threading, bias toward deletion and the smallest change that solves the problem.

- **Consolidate decisions.** Do not repeat the same choice in several places. Put it behind one source of truth and pass the result as a simple flag.
- **Minimize the diff.** Make the smallest change that solves the problem. Fewer lines beat "elegant" boilerplate.
