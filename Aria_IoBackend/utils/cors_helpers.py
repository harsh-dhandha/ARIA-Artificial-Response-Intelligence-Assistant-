from fastapi.responses import PlainTextResponse

def cors_options_response(allowed_methods="POST, OPTIONS"):
    """
    Generate a consistent CORS preflight response for OPTIONS requests.
    
    Args:
        allowed_methods: String of comma-separated HTTP methods to allow
        
    Returns:
        PlainTextResponse with proper CORS headers
    """
    return PlainTextResponse(
        content="",
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",  # Allow all origins
            "Access-Control-Allow-Methods": allowed_methods,
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "86400",
        },
    )
