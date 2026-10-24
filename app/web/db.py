"""SQLite persistence layer with fixture seeding for Render."""
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import aiosqlite
from app.web.config import config


async def get_db_connection(db_path: Optional[str] = None) -> aiosqlite.Connection:
    path = db_path or config.DATABASE_PATH
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = await aiosqlite.connect(path)
    conn.row_factory = aiosqlite.Row
    return conn


async def init_db(db_path: Optional[str] = None) -> None:
    """Initialize SQLite database schema and seed fixtures if empty."""
    conn = await get_db_connection(db_path)
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                run_id TEXT PRIMARY KEY,
                workflow_id TEXT,
                repo_name TEXT,
                branch_name TEXT,
                base_commit TEXT,
                target_commit TEXT,
                status TEXT,
                created_at TEXT,
                completed_at TEXT,
                metrics_json TEXT,
                files_json TEXT,
                unified_diff TEXT,
                sentry_trace_id TEXT,
                error TEXT
            );
        """)
        await conn.commit()

        # Check if table is empty
        cursor = await conn.execute("SELECT COUNT(*) as count FROM reports;")
        row = await cursor.fetchone()
        count = row["count"] if row else 0

        if count == 0:
            await seed_fixtures(conn)
    finally:
        await conn.close()


async def seed_fixtures(conn: aiosqlite.Connection) -> None:
    """Seed demo reports from fixtures/demo_reports.json."""
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "demo_reports.json"
    if not fixture_path.exists():
        return

    try:
        with open(fixture_path, "r", encoding="utf-8") as f:
            demo_data = json.load(f)

        for report in demo_data:
            await conn.execute(
                """
                INSERT OR REPLACE INTO reports (
                    run_id, workflow_id, repo_name, branch_name,
                    base_commit, target_commit, status, created_at,
                    completed_at, metrics_json, files_json, unified_diff,
                    sentry_trace_id, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    report["run_id"],
                    report.get("workflow_id"),
                    report["repo_name"],
                    report["branch_name"],
                    report.get("base_commit", "HEAD"),
                    report.get("target_commit"),
                    report.get("status", "completed"),
                    report.get("created_at"),
                    report.get("completed_at"),
                    json.dumps(report.get("metrics", {})),
                    json.dumps(report.get("files", [])),
                    report.get("unified_diff", ""),
                    report.get("sentry_trace_id"),
                    report.get("error"),
                ),
            )
        await conn.commit()
    except Exception as e:
        print(f"Warning: Failed to seed fixtures: {e}")


async def save_report(report_data: Dict[str, Any], db_path: Optional[str] = None) -> None:
    """Save or update a run report in SQLite."""
    conn = await get_db_connection(db_path)
    try:
        metrics = report_data.get("metrics", {})
        if isinstance(metrics, dict):
            metrics_str = json.dumps(metrics)
        else:
            metrics_str = json.dumps(metrics.model_dump() if hasattr(metrics, "model_dump") else str(metrics))

        files = report_data.get("files", [])
        if isinstance(files, list):
            files_list = [f.model_dump() if hasattr(f, "model_dump") else f for f in files]
            files_str = json.dumps(files_list)
        else:
            files_str = json.dumps([])

        await conn.execute(
            """
            INSERT OR REPLACE INTO reports (
                run_id, workflow_id, repo_name, branch_name,
                base_commit, target_commit, status, created_at,
                completed_at, metrics_json, files_json, unified_diff,
                sentry_trace_id, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                report_data["run_id"],
                report_data.get("workflow_id"),
                report_data["repo_name"],
                report_data["branch_name"],
                report_data.get("base_commit", "HEAD"),
                report_data.get("target_commit"),
                report_data.get("status", "completed"),
                str(report_data.get("created_at", "")),
                str(report_data.get("completed_at", "")),
                metrics_str,
                files_str,
                report_data.get("unified_diff", ""),
                report_data.get("sentry_trace_id"),
                report_data.get("error"),
            ),
        )
        await conn.commit()
    finally:
        await conn.close()


async def get_reports(
    db_path: Optional[str] = None,
    status: Optional[str] = None,
    repo_name: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Retrieve list of reports with optional filters."""
    conn = await get_db_connection(db_path)
    try:
        query = "SELECT * FROM reports"
        clauses = []
        params: List[Any] = []

        if status:
            clauses.append("status = ?")
            params.append(status)
        if repo_name:
            clauses.append("repo_name = ?")
            params.append(repo_name)

        if clauses:
            query += " WHERE " + " AND ".join(clauses)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()

        results = []
        for r in rows:
            results.append(_row_to_dict(r))
        return results
    finally:
        await conn.close()


async def get_report(run_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetch single report by run_id."""
    conn = await get_db_connection(db_path)
    try:
        cursor = await conn.execute("SELECT * FROM reports WHERE run_id = ?;", (run_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return _row_to_dict(row)
    finally:
        await conn.close()


async def get_overview_metrics(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Calculate aggregate stats for overview metrics bar."""
    conn = await get_db_connection(db_path)
    try:
        cursor = await conn.execute("SELECT COUNT(*) as total_runs, COUNT(DISTINCT repo_name) as total_repos FROM reports;")
        counts = await cursor.fetchone()

        cursor = await conn.execute("SELECT metrics_json, sentry_trace_id FROM reports WHERE status = 'completed';")
        rows = await cursor.fetchall()

        total_docstrings = 0
        total_tokens = 0
        total_latency = 0
        latest_trace_id = None

        for r in rows:
            if not latest_trace_id and r["sentry_trace_id"]:
                latest_trace_id = r["sentry_trace_id"]
            try:
                m = json.loads(r["metrics_json"])
                total_docstrings += m.get("docstrings_added", 0)
                total_tokens += m.get("tokens_prompt", 0) + m.get("tokens_completion", 0)
                total_latency += m.get("duration_ms", 0)
            except Exception:
                pass

        avg_latency = int(total_latency / len(rows)) if rows else 0

        return {
            "total_runs": counts["total_runs"] if counts else 0,
            "total_repos": counts["total_repos"] if counts else 0,
            "docstrings_resolved": total_docstrings,
            "tokens_consumed": total_tokens,
            "average_latency_ms": avg_latency,
            "latest_sentry_trace_id": latest_trace_id,
        }
    finally:
        await conn.close()


def _row_to_dict(row: aiosqlite.Row) -> Dict[str, Any]:
    res = dict(row)
    try:
        res["metrics"] = json.loads(res.get("metrics_json") or "{}")
    except Exception:
        res["metrics"] = {}
    try:
        res["files"] = json.loads(res.get("files_json") or "[]")
    except Exception:
        res["files"] = []
    return res
