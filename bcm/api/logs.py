async def get_logs(db_ops):
    """Retrieve audit logs."""
    logs = await db_ops.export_audit_logs()
    return logs
