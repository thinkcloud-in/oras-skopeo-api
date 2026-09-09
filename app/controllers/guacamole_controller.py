import os
import time

import psycopg2
from fastapi import HTTPException

from app.schemas.requests import GuacamoleLogsDeleteRequest, GuacamoleRecordingsDeleteRequest


def _connect_to_db():
    """DB connection details caller se nahi, pod ke environment variables se aate hain
    (host/port/dbname plain env, user/password devraq-postgres-secret se injected)."""
    try:
        host = os.environ["GUAC_DB_HOST"]
        user = os.environ["GUAC_DB_USER"]
        password = os.environ["GUAC_DB_PASSWORD"]
    except KeyError as e:
        raise HTTPException(500, f"Missing required DB environment variable: {e}")

    port = int(os.environ.get("GUAC_DB_PORT", "5432"))
    dbname = os.environ.get("GUAC_DB_NAME", "guacamole")

    try:
        return psycopg2.connect(
            host=host, port=port, dbname=dbname,
            user=user, password=password, connect_timeout=10,
        )
    except Exception as e:
        raise HTTPException(502, f"Could not connect to Guacamole DB: {e}")


def delete_connection_history_logs(req: GuacamoleLogsDeleteRequest):
    """guacamole_connection_history se retention_days se purani rows delete karo."""
    if req.retention_days < 1:
        raise HTTPException(400, "retention_days must be at least 1")

    conn = _connect_to_db()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM guacamole_connection_history "
                    "WHERE start_date < now() - (%s || ' days')::interval",
                    (req.retention_days,),
                )
                deleted = cur.rowcount
    except Exception as e:
        raise HTTPException(500, f"Delete failed: {e}")
    finally:
        conn.close()

    return {
        "status":         "success",
        "table":          "guacamole_connection_history",
        "retention_days": req.retention_days,
        "rows_deleted":   deleted,
    }


def delete_recordings(req: GuacamoleRecordingsDeleteRequest):
    """/recordings ke andar retention_days se purani files delete karo (mtime-based)."""
    if req.retention_days < 1:
        raise HTTPException(400, "retention_days must be at least 1")
    if not os.path.isdir(req.recordings_path):
        raise HTTPException(404, f"Recordings path not found: {req.recordings_path}")

    cutoff = time.time() - (req.retention_days * 86400)
    deleted_files = []
    for root, _, files in os.walk(req.recordings_path):
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                if os.path.getmtime(fpath) < cutoff:
                    os.remove(fpath)
                    deleted_files.append(os.path.relpath(fpath, req.recordings_path))
            except OSError:
                continue

    # Guacamole recordings ek connection-id folder ke andar nested hoti hain --
    # cleanup ke baad khaali reh gaye subfolders bhi hata do.
    for root, dirs, _ in os.walk(req.recordings_path, topdown=False):
        for d in dirs:
            dpath = os.path.join(root, d)
            try:
                if not os.listdir(dpath):
                    os.rmdir(dpath)
            except OSError:
                continue

    return {
        "status":          "success",
        "recordings_path": req.recordings_path,
        "retention_days":  req.retention_days,
        "files_deleted":   len(deleted_files),
        "deleted":         deleted_files,
    }
