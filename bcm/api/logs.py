from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bcm.models import Capability

async def get_capability_names(db_ops):
    """Get mapping of capability IDs to names."""
    capability_names = {}
    async with await db_ops._get_session() as session:
        stmt = select(Capability.id, Capability.name)
        result = await session.execute(stmt)
        for id, name in result:
            capability_names[id] = name
    return capability_names

async def get_logs(db_ops):
    """Retrieve and format audit logs."""
    # First get all capabilities to build name mapping
    capability_names = await get_capability_names(db_ops)

    # Get raw logs
    logs = await db_ops.export_audit_logs()

    # Combine CREATE and ID_ASSIGN operations
    combined_logs = []
    create_log = None

    for log in logs:
        if log["operation"] == "CREATE":
            create_log = log
        elif log["operation"] == "ID_ASSIGN" and create_log:
            # Merge ID_ASSIGN info into CREATE log
            if create_log["capability_name"] == log["capability_name"]:
                create_log["capability_id"] = log["capability_id"]
                continue

        if create_log:
            combined_logs.append(create_log)
            create_log = None

        if log["operation"] != "ID_ASSIGN":
            combined_logs.append(log)

    return combined_logs
