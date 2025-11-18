import time
import logging
from functools import wraps
from typing import Callable, Any
from app.core.config_assessment import assessment_settings

logger = logging.getLogger(__name__)

def monitor_performance(operation_name: str = None):
    """Decorator to monitor function performance"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                if execution_time > assessment_settings.QUERY_TIMEOUT:
                    logger.warning(f"Slow operation detected: {op_name} took {execution_time:.2f}s")
                else:
                    logger.debug(f"Operation completed: {op_name} in {execution_time:.2f}s")
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Operation failed: {op_name} after {execution_time:.2f}s - {str(e)}")
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                if execution_time > assessment_settings.QUERY_TIMEOUT:
                    logger.warning(f"Slow operation detected: {op_name} took {execution_time:.2f}s")
                else:
                    logger.debug(f"Operation completed: {op_name} in {execution_time:.2f}s")
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Operation failed: {op_name} after {execution_time:.2f}s - {str(e)}")
                raise
        
        return async_wrapper if hasattr(func, '__code__') and func.__code__.co_flags & 0x80 else sync_wrapper
    
    return decorator

class PerformanceMetrics:
    """Simple performance metrics collector"""
    def __init__(self):
        self.metrics = {}
    
    def record_operation(self, operation: str, duration: float, success: bool = True):
        """Record operation metrics"""
        if operation not in self.metrics:
            self.metrics[operation] = {
                'count': 0,
                'total_time': 0,
                'failures': 0,
                'avg_time': 0
            }
        
        self.metrics[operation]['count'] += 1
        self.metrics[operation]['total_time'] += duration
        
        if not success:
            self.metrics[operation]['failures'] += 1
        
        self.metrics[operation]['avg_time'] = (
            self.metrics[operation]['total_time'] / self.metrics[operation]['count']
        )
    
    def get_metrics(self) -> dict:
        """Get current metrics"""
        return self.metrics.copy()

# Global metrics instance
performance_metrics = PerformanceMetrics()