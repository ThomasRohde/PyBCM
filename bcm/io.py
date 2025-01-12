import asyncio
import json
import os
from tkinter import filedialog
from bcm.dialogs import create_dialog


def import_capabilities(root, db_ops, loop):
    """Import capabilities from JSON file."""
    user_dir = os.path.expanduser("~")
    app_dir = os.path.join(user_dir, ".pybcm")
    os.makedirs(app_dir, exist_ok=True)
    filename = filedialog.askopenfilename(
        title="Import Capabilities",
        initialdir=app_dir,
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
    )
    if not filename:
        return

    try:
        with open(filename, "r") as f:
            data = json.load(f)

        # Confirm import
        if create_dialog(
            root,
            "Confirm Import",
            "This will replace all existing capabilities. Continue?",
        ):
            # Create coroutine for import operation
            async def import_async():
                await db_ops.import_capabilities(data)

            # Run the coroutine in the event loop
            future = asyncio.run_coroutine_threadsafe(import_async(), loop)
            future.result()  # Wait for completion

            create_dialog(
                root, "Success", "Capabilities imported successfully", ok_only=True
            )

            return True  # Signal success for UI refresh

    except Exception as e:
        create_dialog(
            root, "Error", f"Failed to import capabilities: {str(e)}", ok_only=True
        )
        return False


def export_capabilities(root, db_ops, loop):
    """Export capabilities to JSON file."""
    user_dir = os.path.expanduser("~")
    app_dir = os.path.join(user_dir, ".pybcm")
    os.makedirs(app_dir, exist_ok=True)
    filename = filedialog.asksaveasfilename(
        title="Export Capabilities",
        initialdir=app_dir,
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
    )
    if not filename:
        return

    try:
        # Create coroutine for export operation
        async def export_async():
            data = await db_ops.export_capabilities()
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)

        # Run the coroutine in the event loop
        future = asyncio.run_coroutine_threadsafe(export_async(), loop)
        future.result()  # Wait for completion

        create_dialog(
            root, "Success", "Capabilities exported successfully", ok_only=True
        )

    except Exception as e:
        create_dialog(
            root, "Error", f"Failed to export capabilities: {str(e)}", ok_only=True
        )
