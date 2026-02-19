import asyncio
import httpx

async def test_news():
    url = "http://localhost:8000/api/news"
    payload = {"intent": "What is the latest news for Tesla?"}
    
    async with httpx.AsyncClient() as client:
        print(f"🚀 Sending request to {url}...")
        response = await client.post(url, json=payload)
        
        if response.status_code == 200:
            print("✅ Success!")
            print(response.json())
        else:
            print(f"❌ Failed with status: {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    asyncio.run(test_news())
