# Architecture

```text
Telegram
   |
   v
python-telegram-bot
   |
   v
OpenAI Agents SDK
   |
   +--> inventory tools ------> SQLite
   +--> billing tools --------> SQLite transactions
   +--> khata tools ----------> SQLite
   +--> preferences ----------> SQLite
   +--> PDF tool -------------> ReportLab
   +--> PPTX tool ------------> python-pptx + matplotlib
```

The model is the orchestrator. There is no intent-classification switch statement.

Business invariants are enforced at the tool/database layer:
- stock never goes negative
- selling price cannot be below cost
- draft billing does not mutate stock
- finalization rechecks stock transactionally
- GST is calculated from stored product data
- UPI/Card require references
- khata cannot be settled for nonexistent customers or above balance
- duplicate Telegram update IDs are ignored

SQLite WAL + `BEGIN IMMEDIATE` provides a simple concurrency foundation for this single-store assignment. A production multi-instance deployment would move the transactional store to PostgreSQL.
