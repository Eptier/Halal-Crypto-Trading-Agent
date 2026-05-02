"""SQLite-backed trade & P&L ledger (async via aiosqlite)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    mode TEXT NOT NULL,                   -- 'paper' | 'live'
    side TEXT NOT NULL,                   -- 'buy' | 'sell'
    pair TEXT NOT NULL,
    base_amount REAL NOT NULL,
    quote_amount REAL NOT NULL,
    price REAL NOT NULL,
    rationale TEXT
);

CREATE TABLE IF NOT EXISTS positions (
    pair TEXT PRIMARY KEY,
    base_amount REAL NOT NULL,
    avg_entry_price REAL NOT NULL,
    opened_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS equity_snapshots (
    ts TEXT PRIMARY KEY,
    equity REAL NOT NULL
);
"""


@dataclass
class TradeRow:
    ts: str
    mode: str
    side: str
    pair: str
    base_amount: float
    quote_amount: float
    price: float
    rationale: str


class Ledger:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

    async def init(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

    async def record_trade(self, row: TradeRow) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO trades(ts,mode,side,pair,base_amount,quote_amount,price,rationale) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    row.ts,
                    row.mode,
                    row.side,
                    row.pair,
                    row.base_amount,
                    row.quote_amount,
                    row.price,
                    row.rationale,
                ),
            )
            await db.commit()

    async def upsert_position(
        self, pair: str, base_amount: float, avg_entry_price: float
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            now = datetime.now(UTC).isoformat()
            await db.execute(
                "INSERT INTO positions(pair,base_amount,avg_entry_price,opened_at) "
                "VALUES(?,?,?,?) "
                "ON CONFLICT(pair) DO UPDATE SET "
                "  base_amount=excluded.base_amount, "
                "  avg_entry_price=excluded.avg_entry_price",
                (pair, base_amount, avg_entry_price, now),
            )
            await db.commit()

    async def delete_position(self, pair: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM positions WHERE pair=?", (pair,))
            await db.commit()

    async def list_positions(self) -> list[tuple[str, float, float, str]]:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "SELECT pair,base_amount,avg_entry_price,opened_at FROM positions"
            )
            rows = await cur.fetchall()
            return [(str(r[0]), float(r[1]), float(r[2]), str(r[3])) for r in rows]

    async def get_position(self, pair: str) -> tuple[float, float] | None:
        """Return (base_amount, avg_entry_price) for the pair, or None if absent."""
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "SELECT base_amount,avg_entry_price FROM positions WHERE pair=?",
                (pair,),
            )
            row = await cur.fetchone()
            if row is None:
                return None
            return float(row[0]), float(row[1])

    async def record_equity(self, equity: float) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO equity_snapshots(ts,equity) VALUES(?,?)",
                (datetime.now(UTC).isoformat(), equity),
            )
            await db.commit()

    async def recent_trades(self, limit: int = 50) -> list[tuple]:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "SELECT ts,mode,side,pair,base_amount,quote_amount,price,rationale "
                "FROM trades ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = await cur.fetchall()
            return [tuple(r) for r in rows]
