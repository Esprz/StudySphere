import Redis from 'ioredis';

const REDIS_HOST = process.env.REDIS_HOST || 'redis';
const REDIS_PORT = parseInt(process.env.REDIS_PORT || '6379', 10);
const REDIS_PASSWORD = process.env.REDIS_PASSWORD || undefined;
const REDIS_DB = parseInt(process.env.REDIS_CACHE_DB || '1', 10);

const redis = new Redis({
  host: REDIS_HOST,
  port: REDIS_PORT,
  password: REDIS_PASSWORD,
  db: REDIS_DB,
  retryStrategy(times: number) {
    if (times > 5) return null;
    return Math.min(times * 200, 2000);
  },
  lazyConnect: true,
});

let connected = false;

redis.on('connect', () => {
  connected = true;
  console.log('Redis cache connected');
});

redis.on('error', (err: Error) => {
  connected = false;
  console.error('Redis cache error:', err.message);
});

export async function initRedis(): Promise<void> {
  try {
    await redis.connect();
  } catch {
    console.warn('Redis unavailable — recommendations will fall back to Postgres');
  }
}

export function isRedisConnected(): boolean {
  return connected;
}

export default redis;
