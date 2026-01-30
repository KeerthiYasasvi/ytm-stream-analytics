# Bot Performance Signals

This repository uses labels to score real-world bot performance. Add these labels to issues after reviewing the bot's response.

## Labels and scoring
- `bot:helpful` (+2) — response was accurate and useful
- `bot:resolved` (+2) — issue resolved without maintainer escalation
- `bot:off-topic-correct` (+1) — bot correctly redirected off-topic comment
- `bot:needs-work` (-2) — response was low quality or confusing
- `bot:wrong-category` (-2) — bot chose the wrong category
- `bot:off-topic-wrong` (-1) — bot incorrectly flagged as off-topic
- `bot:escalated` (0) — escalated to maintainer review (neutral)

## How it’s used
A weekly workflow aggregates these labels and telemetry (token usage + loops) into a performance summary.

## Tips
- Apply labels after the bot’s response so we capture the final outcome.
- Use `bot:needs-work` and `bot:wrong-category` to flag regressions quickly.
