import uvicorn
import sys
import os

# Ensure the root of the project is in the path
# This allows 'from staging_transactions.database import ...' to work everywhere
root_path = os.path.dirname(os.path.abspath(__file__))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

if __name__ == "__main__":
    # IMPORTANT: Remove reload=True while debugging to prevent the debugger
    # from losing the process connection during a restart.
    uvicorn.run(
        "staging_transactions.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="debug",
    )
