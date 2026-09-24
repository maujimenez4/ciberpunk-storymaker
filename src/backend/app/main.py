from fastapi import FastAPI


def crear_app() -> FastAPI:
    app = FastAPI(title="ciberpunk-storymaker", version="0.1.0")
    return app
