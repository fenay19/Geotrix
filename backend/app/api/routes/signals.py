from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_signals():
    return {"message": "Signals route placeholder"}
