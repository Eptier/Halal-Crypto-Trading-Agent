"""Allow running with: python -m silent_money_machine"""

import uvicorn

from silent_money_machine.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "silent_money_machine.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
    )
