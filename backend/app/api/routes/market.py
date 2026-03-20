from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_market():
    return {"message": "Market route placeholder"}
