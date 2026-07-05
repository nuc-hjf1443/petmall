from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers import adoption_router, admin_router, agent_router, auth_router, merchant_router, user_router
from settings.config import get_settings


settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/generated",
    StaticFiles(directory=str(settings.generated_asset_path), check_dir=False),
    name="generated",
)

app.include_router(auth_router.router)
app.include_router(user_router.router)
app.include_router(adoption_router.router)
app.include_router(merchant_router.router)
app.include_router(admin_router.router)
app.include_router(agent_router.router)


@app.get("/")
async def root():
    return {"message": settings.app_name}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}
