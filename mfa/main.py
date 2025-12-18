from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mfa.infrastructure.routes import router as mfa_router

app = FastAPI(title="MFA Authenticator")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mfa_router)


@app.get("/")
def index():
    return {"message": "MFA Authenticator"}