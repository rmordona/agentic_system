class BookingService:

    async def book_flight(
        self,
        from_airport: str,
        to_airport: str,
        date: str,
        passenger_name: str,
    ):
        # Replace with real booking integration
        return {
            "confirmation": "ABC123",
            "route": f"{from_airport} → {to_airport}",
            "date": date,
            "passenger": passenger_name,
        }

booking_service = BookingService()

