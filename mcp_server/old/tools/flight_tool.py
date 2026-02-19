from app.mcp import mcp
from app.services.booking_service import booking_service

@mcp.tool()
async def book_flight(
    from_airport: str,
    to_airport: str,
    date: str,
    passenger_name: str,
):
    """
    Book a flight between two airports for a passenger.
    """
    return await booking_service.book_flight(
        from_airport,
        to_airport,
        date,
        passenger_name,
    )

