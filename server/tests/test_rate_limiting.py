import asyncio
import aiohttp
import time
import json

async def test_auth_rate_limiting():
    """Test rate limiting on auth endpoints"""
    print("Testing auth endpoint rate limiting...")
    login_url = "http://localhost:3001/api/auth/token"
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(6):
            login_data = {
                "username": f"test{i}@example.com",
                "password": "wrongpassword"
            }
            task = asyncio.ensure_future(
                session.post(login_url, data=login_data)
            )
            tasks.append(task)
            
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        request_count = 0
        rate_limited_count = 0
        
        for response in responses:
            if isinstance(response, Exception):
                print(f"Request failed with error: {response}")
                continue
                
            request_count += 1
            if response.status == 429:
                rate_limited_count += 1
                retry_after = response.headers.get("Retry-After")
                print(f"Rate limited with Retry-After: {retry_after}")
                
        print(f"Total requests: {request_count}")
        print(f"Rate limited requests: {rate_limited_count}")
        print(f"Expected behavior: At least 1 request should be rate limited")
        
if __name__ == "__main__":
    asyncio.run(test_auth_rate_limiting())
