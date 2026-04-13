"""Entry point for the mock server."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "server.mock.app:app",
        host="0.0.0.0",
        port=8100,
        reload=True,
        reload_dirs=["server/mock"],
        log_level="info",
    )
