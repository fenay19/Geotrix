from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_gti():
    return {"message": "GTI route placeholder"}
