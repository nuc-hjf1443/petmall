from sqlalchemy.ext.asyncio import AsyncSession

from models.audit import AdminActionLog, AuditLog


async def write_audit_log(
    db: AsyncSession,
    *,
    target_type: str,
    target_id: int,
    action: str,
    result: str,
    operator_id: int,
    reason: str | None = None,
) -> AuditLog:
    log = AuditLog(
        target_type=target_type,
        target_id=target_id,
        action=action,
        result=result,
        operator_id=operator_id,
        reason=reason,
    )
    db.add(log)
    await db.flush()
    return log


async def write_admin_action_log(
    db: AsyncSession,
    *,
    admin_id: int,
    action: str,
    target_type: str,
    target_id: int,
    reason: str | None = None,
) -> AdminActionLog:
    log = AdminActionLog(
        admin_id=admin_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
    )
    db.add(log)
    await db.flush()
    return log
