from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()

@router.options("/{full_path:path}")
async def options_handler(full_path: str):
    """
    Global OPTIONS handler for preflight CORS requests
    This will handle OPTIONS requests for all routes
    """
    return PlainTextResponse(
        status_code=200,
        content="",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
            "Access-Control-Max-Age": "86400",
        },
    )
