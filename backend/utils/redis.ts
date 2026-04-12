import Redis from 'ioredis';

type RedisTarget = 'cache' | 'session';

type CircuitState = {
  failures: number;
  openUntil: number;
};

const DEFAULT_PORT = 6379;
const FAILURE_THRESHOLD = 3;
const COOLDOWN_MS = 30_000;
const SESSION_TTL_SECONDS = 60 * 60 * 24;

const REDIS_PASSWORD = process.env.REDIS_PASSWORD || undefined;

const cacheRedis = new Redis({
  host: process.env.REDIS_CACHE_HOST || process.env.REDIS_HOST || 'redis-cache',
  port: parseInt(process.env.REDIS_CACHE_PORT || process.env.REDIS_PORT || `${DEFAULT_PORT}`, 10),
  password: REDIS_PASSWORD,
  db: parseInt(process.env.REDIS_CACHE_DB || '1', 10),
  retryStrategy(times: number) {
    if (times > 5) return null;
    return Math.min(times * 200, 2000);
  },
  lazyConnect: true,
});

const sessionRedis = new Redis({
  host: process.env.REDIS_SESSION_HOST || process.env.REDIS_HOST || 'redis-session',
  port: parseInt(process.env.REDIS_SESSION_PORT || process.env.REDIS_PORT || `${DEFAULT_PORT}`, 10),
  password: REDIS_PASSWORD,
  db: parseInt(process.env.REDIS_SESSION_DB || '0', 10),
  retryStrategy(times: number) {
    if (times > 5) return null;
    return Math.min(times * 200, 2000);
  },
  lazyConnect: true,
});

let cacheConnected = false;
let sessionConnected = false;

const circuitState: Record<RedisTarget, CircuitState> = {
  cache: { failures: 0, openUntil: 0 },
  session: { failures: 0, openUntil: 0 },
};

const markSuccess = (target: RedisTarget) => {
  circuitState[target] = { failures: 0, openUntil: 0 };
};

const markFailure = (target: RedisTarget) => {
  const nextFailures = circuitState[target].failures + 1;
  circuitState[target].failures = nextFailures;
  if (nextFailures >= FAILURE_THRESHOLD) {
    circuitState[target].openUntil = Date.now() + COOLDOWN_MS;
  }
};

const isCircuitOpen = (target: RedisTarget) =>
  circuitState[target].openUntil > Date.now();

const withCircuitBreaker = async <T>(
  target: RedisTarget,
  operation: () => Promise<T>
): Promise<T> => {
  if (isCircuitOpen(target)) {
    throw new Error(`${target} Redis circuit is open`);
  }

  try {
    const result = await operation();
    markSuccess(target);
    return result;
  } catch (error) {
    markFailure(target);
    throw error;
  }
};

cacheRedis.on('connect', () => {
  cacheConnected = true;
  console.log('Redis cache connected');
});

cacheRedis.on('error', (err: Error) => {
  cacheConnected = false;
  console.error('Redis cache error:', err.message);
});

sessionRedis.on('connect', () => {
  sessionConnected = true;
  console.log('Redis session connected');
});

sessionRedis.on('error', (err: Error) => {
  sessionConnected = false;
  console.error('Redis session error:', err.message);
});

export async function initRedis(): Promise<void> {
  try {
    await cacheRedis.connect();
  } catch {
    console.warn('Redis cache unavailable — recommendations will fall back to Postgres');
  }

  try {
    await sessionRedis.connect();
  } catch {
    console.warn('Redis session unavailable — continuing without session persistence');
  }
}

export function isRedisConnected(): boolean {
  return cacheConnected;
}

export function isRedisCacheConnected(): boolean {
  return cacheConnected;
}

export function isRedisSessionConnected(): boolean {
  return sessionConnected;
}

export async function readCacheValue(key: string): Promise<string | null> {
  if (!isRedisCacheConnected()) {
    return null;
  }

  try {
    return await withCircuitBreaker('cache', () => cacheRedis.get(key));
  } catch (error) {
    console.warn('Redis cache read failed:', (error as Error).message);
    return null;
  }
}

export async function persistSessionContext(sessionId: string): Promise<void> {
  if (!isRedisSessionConnected()) {
    return;
  }

  try {
    await withCircuitBreaker('session', () =>
      sessionRedis.setex(
        `session:${sessionId}`,
        SESSION_TTL_SECONDS,
        JSON.stringify({ touchedAt: new Date().toISOString() })
      )
    );
  } catch (error) {
    console.warn('Redis session write failed:', (error as Error).message);
  }
}

export { cacheRedis, sessionRedis };
export default cacheRedis;
