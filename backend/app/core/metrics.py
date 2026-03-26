"""
Prometheus 监控指标
"""
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest, CONTENT_TYPE_LATEST
from functools import wraps
import time

# 应用信息
APP_INFO = Info("nyx_ai", "NyxAI Application Information")

# HTTP 请求指标
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"]
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# 业务指标
CREDIT_OPERATIONS = Counter(
    "credit_operations_total",
    "Credit operations",
    ["operation", "type"]  # operation: deduct/recharge, type: chat/tti/tts/polish
)

LLM_REQUESTS = Counter(
    "llm_requests_total",
    "LLM API requests",
    ["provider", "status"]  # provider: openrouter/openai, status: success/error
)

LLM_REQUEST_DURATION = Histogram(
    "llm_request_duration_seconds",
    "LLM API request duration",
    ["provider"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

IMAGE_GENERATION = Counter(
    "image_generation_total",
    "Image generation requests",
    ["status"]  # status: success/failed
)

TTS_REQUESTS = Counter(
    "tts_requests_total",
    "TTS requests",
    ["status", "source"]  # status: success/failed, source: api/cache
)

# 系统指标
ACTIVE_USERS = Gauge(
    "active_users",
    "Number of active users"
)

DB_CONNECTIONS = Gauge(
    "db_connections",
    "Database connection pool stats",
    ["state"]  # state: used/available
)


def track_request_duration(method: str, endpoint: str):
    """追踪请求耗时装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                status = "200"
                return result
            except Exception as e:
                status = "500"
                raise
            finally:
                duration = time.time() - start_time
                HTTP_REQUEST_DURATION.labels(
                    method=method, endpoint=endpoint).observe(duration)
                HTTP_REQUESTS_TOTAL.labels(
                    method=method, endpoint=endpoint, status_code=status).inc()
        return wrapper
    return decorator


def track_llm_request(provider: str):
    """追踪 LLM 请求装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                LLM_REQUESTS.labels(provider=provider, status="success").inc()
                return result
            except Exception as e:
                LLM_REQUESTS.labels(provider=provider, status="error").inc()
                raise
            finally:
                duration = time.time() - start_time
                LLM_REQUEST_DURATION.labels(
                    provider=provider).observe(duration)
        return wrapper
    return decorator


def get_metrics():
    """获取 Prometheus 格式的指标数据"""
    return generate_latest()
