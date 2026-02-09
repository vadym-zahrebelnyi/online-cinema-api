from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Pages"])


@router.get(
    "/payment/success",
    response_class=HTMLResponse,
    summary="Render payment success page",
    responses={
        200: {
            "description": "HTML confirmation page",
            "content": {"text/html": {}},
        }
    },
)
async def payment_success_page(session_id: str):
    """
    Serve the static HTML page for successful payment confirmation.

    This endpoint acts as the 'success_url' target for the Stripe Checkout session.
    It displays a confirmation message and the transaction session ID to the user.

    Args:
        session_id (str): The unique session identifier returned by Stripe
            as a query parameter.

    Returns:
        HTMLResponse: A rendered HTML page with success details.
    """
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Payment Successful</title>
        <style>
            body {{
                font-family: 'Helvetica Neue', Arial, sans-serif;
                background-color: #f4f4f9;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }}
            .card {{
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                text-align: center;
                max-width: 400px;
            }}
            .icon {{
                color: #28a745;
                font-size: 60px;
                margin-bottom: 20px;
            }}
            h1 {{ color: #333; margin-bottom: 10px; }}
            p {{ color: #666; margin-bottom: 30px; }}
            .btn {{
                background-color: #007bff;
                color: white;
                padding: 12px 25px;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
                transition: background 0.3s;
            }}
            .btn:hover {{ background-color: #0056b3; }}
            .session-id {{ 
                font-size: 12px; 
                color: #999; 
                margin-top: 20px; 
                word-break: break-all;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">✓</div>
            <h1>Payment Successful!</h1>
            <p>Thank you for your purchase. Your order has been confirmed.</p>
            <a href="/docs" class="btn">Back to API Docs</a>
            <div class="session-id">Session ID: {session_id}</div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


@router.get(
    "/payment/cancel",
    response_class=HTMLResponse,
    summary="Render payment cancellation page",
    responses={
        200: {
            "description": "HTML cancellation page",
            "content": {"text/html": {}},
        }
    },
)
async def payment_cancel_page():
    """
    Serve the static HTML page for payment cancellation.

    This endpoint acts as the 'cancel_url' target for the Stripe Checkout session.
    It is rendered when the user explicitly cancels the payment process or backtracks
    during checkout.

    Returns:
        HTMLResponse: A rendered HTML page indicating the payment was not completed.
    """
    return HTMLResponse(
        content="<h1>Payment Cancelled</h1><p>You can try again anytime.</p>"
    )
