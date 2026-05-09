from datetime import datetime
from typing import Dict, List, Tuple

from db import get_db_connection


def get_system_summary() -> Tuple[bool, Dict]:
    """Return basic system counters for admin dashboard."""

    conn = get_db_connection()
    if not conn:
        return False, {}

    cursor = None
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(1) FROM users")
        users_count = int((cursor.fetchone() or [0])[0] or 0)

        cursor.execute("SELECT COUNT(1) FROM key_pairs")
        key_pairs_count = int((cursor.fetchone() or [0])[0] or 0)

        cursor.execute("SELECT COUNT(1) FROM certificates")
        certificates_count = int((cursor.fetchone() or [0])[0] or 0)

        cursor.execute(
            """
            SELECT COUNT(1)
            FROM certificate_requests
            WHERE request_status = 'pending'
            """
        )
        pending_requests = int((cursor.fetchone() or [0])[0] or 0)

        cursor.execute(
            """
            SELECT COUNT(1)
            FROM certificates c
            OUTER APPLY (
                SELECT TOP 1 status
                FROM certificate_status cs
                WHERE cs.certificate_id = c.id
                ORDER BY cs.changed_at DESC, cs.id DESC
            ) s
            WHERE s.status = 'revoked'
            """
        )
        revoked_certs = int((cursor.fetchone() or [0])[0] or 0)

        return (
            True,
            {
                "users_count": users_count,
                "key_pairs_count": key_pairs_count,
                "certificates_count": certificates_count,
                "pending_requests": pending_requests,
                "revoked_certs": revoked_certs,
            },
        )

    except Exception:
        return False, {}

    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        conn.close()


def list_recent_activity(limit: int = 20) -> Tuple[bool, List[Dict]]:
    """Return recent activity events for admin dashboard.

    Events include:
    - Certificate request submitted
    - Certificate request reviewed (approved/rejected/completed)
    - Certificate revoked
    """

    limit = int(limit or 20)
    if limit <= 0:
        limit = 20
    if limit > 200:
        limit = 200

    conn = get_db_connection()
    if not conn:
        return False, []

    cursor = None
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT TOP (?)
                e.event_time,
                e.event_type,
                e.actor,
                e.target,
                e.details
            FROM (
                SELECT
                    r.submitted_at AS event_time,
                    'request_submitted' AS event_type,
                    u.username AS actor,
                    CONCAT('request#', r.id) AS target,
                    CONCAT(r.request_type, ' / ', r.request_status,
                           CASE WHEN r.domain_name IS NULL THEN '' ELSE CONCAT(' / ', r.domain_name) END) AS details
                FROM certificate_requests r
                INNER JOIN users u ON u.id = r.user_id

                UNION ALL

                SELECT
                    r.reviewed_at AS event_time,
                    'request_reviewed' AS event_type,
                    COALESCE(au.username, CONCAT('admin#', CAST(r.reviewed_by_admin_id AS NVARCHAR(50)))) AS actor,
                    CONCAT('request#', r.id) AS target,
                    CONCAT(r.request_type, ' / ', r.request_status,
                           CASE WHEN r.domain_name IS NULL THEN '' ELSE CONCAT(' / ', r.domain_name) END) AS details
                FROM certificate_requests r
                LEFT JOIN users au ON au.id = r.reviewed_by_admin_id
                WHERE r.reviewed_at IS NOT NULL

                UNION ALL

                SELECT
                    cs.changed_at AS event_time,
                    'certificate_revoked' AS event_type,
                    COALESCE(au.username, CONCAT('admin#', CAST(cs.changed_by_admin_id AS NVARCHAR(50)))) AS actor,
                    CONCAT('cert#', cs.certificate_id) AS target,
                    CONCAT('revoked',
                           CASE WHEN cs.revocation_reason_code IS NULL THEN '' ELSE CONCAT(' / ', cs.revocation_reason_code) END) AS details
                FROM certificate_status cs
                LEFT JOIN users au ON au.id = cs.changed_by_admin_id
                WHERE cs.status = 'revoked'
            ) e
            WHERE e.event_time IS NOT NULL
            ORDER BY e.event_time DESC
            """,
            (limit,),
        )

        rows = cursor.fetchall() or []
        columns = [col[0] for col in cursor.description]

        data: List[Dict] = []
        for row in rows:
            item = dict(zip(columns, row))
            for k, v in list(item.items()):
                if isinstance(v, datetime):
                    item[k] = v.isoformat(sep=" ", timespec="seconds")
            data.append(item)

        return True, data

    except Exception:
        return False, []

    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass
        conn.close()
