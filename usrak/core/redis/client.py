from redis.asyncio import Redis

from usrak import config

redis = Redis.from_url(config.REDIS_URL, encoding="utf-8", decode_responses=True)
