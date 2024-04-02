from fastapi import FastAPI, Request, HTTPException
import redis
import time

app = FastAPI()
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)


# Function to check and enforce rate limits
def rate_limit_exceeded(key, limit, window):
    current_time = int(time.time())
    key = f"rate_limit:{key}"
    # Store current timestamp if key doesn't exist
    redis_client.setnx(key, f"{current_time}:0")

    # Split value into timestamp and count
    last_time, count = redis_client.get(key).decode().split(':')

    last_time, count = int(last_time), int(count)
    # If last request was outside current window, reset count

    if current_time - last_time > window:
        count = 0
        redis_client.set(key, f"{current_time}:{count}")
    else:
        count += 1
        redis_client.set(key, f"{last_time}:{count}")

    # Check if rate limit exceeded
    return count > limit


# Middleware to enforce rate limits
@app.middleware("http")
async def limit_requests(request: Request, call_next):
    user_id = request.headers.get('X-User-ID')  # Assuming user ID is passed in header
    ip_address = request.client.host
    if user_id:
        key = f"user_id:{user_id}"
        if rate_limit_exceeded(key, limit=100, window=3600):  # Example: 100 requests per hour
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
    if ip_address:
        key = f"ip:{ip_address}"
        if rate_limit_exceeded(key, limit=200, window=3600):  # Example: 200 requests per hour
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
    response = await call_next(request)
    return response


# Example route
@app.get('/')
async def index():
    return {"message": "Hello, World!"}


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
