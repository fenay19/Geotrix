from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_chatbot():
    return {"message": "Chatbot route placeholder"}
