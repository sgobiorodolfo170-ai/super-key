import uvicorn
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        workers=4,
        reload=False,
        log_level=settings.log_level.lower(),
    )
