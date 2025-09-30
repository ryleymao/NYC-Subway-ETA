"""
Performance monitoring utilities for NYC Subway ETA API
"""
import time
import logging
from functools import wraps
from typing import Callable, Any
import psutil
import structlog

logger = structlog.get_logger(__name__)

class PerformanceMonitor:
    """Monitor API performance and system resources"""

    def __init__(self):
        self.request_times = []
        self.memory_usage = []

    def log_request_time(self, endpoint: str, duration: float):
        """Log API request timing"""
        self.request_times.append({
            'endpoint': endpoint,
            'duration': duration,
            'timestamp': time.time()
        })

        if duration > 1.0:  # Log slow requests
            logger.warning(f"Slow request: {endpoint} took {duration:.3f}s")

    def log_memory_usage(self):
        """Log current memory usage"""
        memory = psutil.virtual_memory()
        self.memory_usage.append({
            'percent': memory.percent,
            'available': memory.available / 1024 / 1024,  # MB
            'timestamp': time.time()
        })

        if memory.percent > 85:
            logger.warning(f"High memory usage: {memory.percent}%")

    def get_performance_stats(self) -> dict:
        """Get performance statistics"""
        recent_requests = [r for r in self.request_times
                          if time.time() - r['timestamp'] < 300]  # Last 5 minutes

        if recent_requests:
            avg_response_time = sum(r['duration'] for r in recent_requests) / len(recent_requests)
            max_response_time = max(r['duration'] for r in recent_requests)
        else:
            avg_response_time = 0
            max_response_time = 0

        return {
            'avg_response_time': avg_response_time,
            'max_response_time': max_response_time,
            'total_requests': len(recent_requests),
            'memory_percent': psutil.virtual_memory().percent
        }

def monitor_performance(func: Callable) -> Callable:
    """Decorator to monitor function performance"""
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start_time
            endpoint = getattr(func, '__name__', 'unknown')
            monitor.log_request_time(endpoint, duration)

    return wrapper

# Global monitor instance
monitor = PerformanceMonitor()