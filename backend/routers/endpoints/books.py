
from fastapi import APIRouter

router = APIRouter()

@router.get("/id")
def get_book():
    return {"ну рыбает и хули спотришь":"lol"}
