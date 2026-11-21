from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from .auth import verify_api_token
from .ssh import execute_by_id, COMMAND_REGISTRY

app = FastAPI(title="Katana SSH Bridge", version="1.1.0")

class CommandRequest(BaseModel):
    command_id: str = Field(..., min_length=1, description="Key from COMMAND_REGISTRY")

class CommandResponse(BaseModel):
    success: bool
    exit_code: int
    stdout: str
    stderr: str

@app.post("/execute", response_model=CommandResponse, dependencies=[Depends(verify_api_token)])
async def execute(request: CommandRequest):
    return await execute_by_id(request.command_id.strip())

@app.get("/commands", dependencies=[Depends(verify_api_token)])
async def list_commands():
    return {"allowed": sorted(COMMAND_REGISTRY.keys())}

@app.get("/health")
async def health():
    return {"status": "healthy"}
