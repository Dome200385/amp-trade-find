from app.services.unified_validation import validation_counts_unified

def lifecycle_health():
    data = validation_counts_unified()
    return {
        "counts": data["counts"],
        "waiting_entry": data["waiting_entry"],
        "active": data["active"],
        "resolved": data["resolved"],
        "missed_entry": data["missed_entry"],
        "open_total": data["waiting_entry"] + data["active"],
        "healthy": True,
        "reason": None,
    }
