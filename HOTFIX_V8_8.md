# AMP TRADE FIND V8.8 – Persistent Storage

Purpose:
Use Render Persistent Disk mounted at:

/var/data

Primary SQLite database:
 /var/data/amp_trade_find.db

Persistent probe:
 /var/data/amp_find_persistence_probe.json

All existing SQLite-backed features share the same database:
- signal history
- validation setups
- push device registry
- persistence metadata

Startup now:
1. ensure /var/data exists and is writable
2. open SQLite database
3. enable WAL mode
4. initialize persistence metadata
5. initialize signal / push / validation tables
6. start live loops

New endpoint:
GET /api/v1/persistence/status

Recommended test after deploy:
1. open /api/v1/persistence/status
2. note database_size_bytes and table_counts
3. let FIND run
4. restart service in Render
5. reopen /api/v1/persistence/status
6. verify database still exists and counts are preserved

Expected database path:
 /var/data/amp_trade_find.db

Important:
The Render disk must be mounted at /var/data.
