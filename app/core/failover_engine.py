"""
Phase 10.3 - Failover & Resilience Engine
Enterprise-grade fault tolerance for external services.
"""

from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import time
import random


class ServiceStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    DOWN = "down"


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    recovery_timeout: int = 60
    half_open_requests: int = 3
    
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    state: str = "closed"
    successful_half_open: int = 0


@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class ServiceHealth:
    service: str
    status: ServiceStatus
    last_check: datetime
    latency_ms: float
    error_rate: float
    consecutive_failures: int


class FailoverEngine:
    """Resilience and failover management for external services."""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.service_health: Dict[str, ServiceHealth] = {}
        self.fallback_handlers: Dict[str, Callable] = {}
        self.request_queue: Dict[str, List[Dict]] = {}
        
        self._init_circuit_breakers()
    
    def _init_circuit_breakers(self):
        """Initialize circuit breakers for external services."""
        services = [
            "google_calendar",
            "twilio_voice",
            "twilio_sms",
            "openai_chat",
            "openai_realtime",
            "stripe",
            "database"
        ]
        
        for service in services:
            self.circuit_breakers[service] = CircuitBreaker(name=service)
            self.service_health[service] = ServiceHealth(
                service=service,
                status=ServiceStatus.HEALTHY,
                last_check=datetime.now(),
                latency_ms=0,
                error_rate=0,
                consecutive_failures=0
            )
    
    def register_fallback(self, service: str, handler: Callable):
        """Register a fallback handler for a service."""
        self.fallback_handlers[service] = handler
    
    async def execute_with_retry(
        self,
        service: str,
        operation: Callable,
        *args,
        retry_config: RetryConfig = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute operation with exponential backoff retry."""
        config = retry_config or RetryConfig()
        cb = self.circuit_breakers.get(service)
        
        if cb and cb.state == "open":
            if self._should_attempt_recovery(cb):
                cb.state = "half-open"
            else:
                return await self._execute_fallback(service, *args, **kwargs)
        
        last_error = None
        
        for attempt in range(config.max_retries + 1):
            try:
                start_time = time.time()
                
                if asyncio.iscoroutinefunction(operation):
                    result = await operation(*args, **kwargs)
                else:
                    result = operation(*args, **kwargs)
                
                latency = (time.time() - start_time) * 1000
                
                self._record_success(service, latency)
                
                return {"success": True, "result": result, "attempts": attempt + 1}
                
            except Exception as e:
                last_error = e
                self._record_failure(service, str(e))
                
                if attempt < config.max_retries:
                    delay = self._calculate_delay(config, attempt)
                    await asyncio.sleep(delay)
        
        return await self._execute_fallback(service, *args, error=str(last_error), **kwargs)
    
    def _calculate_delay(self, config: RetryConfig, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter."""
        delay = min(
            config.base_delay * (config.exponential_base ** attempt),
            config.max_delay
        )
        
        if config.jitter:
            delay = delay * (0.5 + random.random())
        
        return delay
    
    def _should_attempt_recovery(self, cb: CircuitBreaker) -> bool:
        """Check if circuit breaker should attempt recovery."""
        if not cb.last_failure_time:
            return True
        
        elapsed = (datetime.now() - cb.last_failure_time).total_seconds()
        return elapsed >= cb.recovery_timeout
    
    def _record_success(self, service: str, latency_ms: float):
        """Record successful operation."""
        cb = self.circuit_breakers.get(service)
        health = self.service_health.get(service)
        
        if cb:
            if cb.state == "half-open":
                cb.successful_half_open += 1
                if cb.successful_half_open >= cb.half_open_requests:
                    cb.state = "closed"
                    cb.failure_count = 0
                    cb.successful_half_open = 0
            else:
                cb.failure_count = max(0, cb.failure_count - 1)
        
        if health:
            health.status = ServiceStatus.HEALTHY
            health.latency_ms = latency_ms
            health.consecutive_failures = 0
            health.last_check = datetime.now()
    
    def _record_failure(self, service: str, error: str):
        """Record failed operation."""
        cb = self.circuit_breakers.get(service)
        health = self.service_health.get(service)
        
        if cb:
            cb.failure_count += 1
            cb.last_failure_time = datetime.now()
            
            if cb.state == "half-open":
                cb.state = "open"
                cb.successful_half_open = 0
            elif cb.failure_count >= cb.failure_threshold:
                cb.state = "open"
        
        if health:
            health.consecutive_failures += 1
            health.last_check = datetime.now()
            
            if health.consecutive_failures >= 3:
                health.status = ServiceStatus.FAILING
            elif health.consecutive_failures >= 1:
                health.status = ServiceStatus.DEGRADED
    
    async def _execute_fallback(
        self,
        service: str,
        *args,
        error: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute fallback handler for a service."""
        handler = self.fallback_handlers.get(service)
        
        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(*args, **kwargs)
                else:
                    result = handler(*args, **kwargs)
                
                return {
                    "success": True,
                    "result": result,
                    "fallback": True,
                    "original_error": error
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "fallback_failed": True,
                    "original_error": error
                }
        
        return {
            "success": False,
            "error": error or "Service unavailable",
            "no_fallback": True
        }
    
    def queue_request(self, service: str, request_data: Dict[str, Any]):
        """Queue a request for later retry."""
        if service not in self.request_queue:
            self.request_queue[service] = []
        
        self.request_queue[service].append({
            "data": request_data,
            "queued_at": datetime.now().isoformat(),
            "attempts": 0
        })
    
    async def process_queue(self, service: str, processor: Callable) -> List[Dict]:
        """Process queued requests for a service."""
        if service not in self.request_queue:
            return []
        
        results = []
        remaining = []
        
        for item in self.request_queue[service]:
            try:
                if asyncio.iscoroutinefunction(processor):
                    result = await processor(item["data"])
                else:
                    result = processor(item["data"])
                
                results.append({"success": True, "result": result})
                
            except Exception as e:
                item["attempts"] += 1
                if item["attempts"] < 3:
                    remaining.append(item)
                results.append({"success": False, "error": str(e)})
        
        self.request_queue[service] = remaining
        
        return results
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of all monitored services."""
        status = {}
        
        for service, health in self.service_health.items():
            cb = self.circuit_breakers.get(service)
            
            status[service] = {
                "status": health.status.value,
                "latency_ms": health.latency_ms,
                "consecutive_failures": health.consecutive_failures,
                "last_check": health.last_check.isoformat(),
                "circuit_breaker": cb.state if cb else "unknown"
            }
        
        return status
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall health summary."""
        total = len(self.service_health)
        healthy = sum(1 for h in self.service_health.values() if h.status == ServiceStatus.HEALTHY)
        degraded = sum(1 for h in self.service_health.values() if h.status == ServiceStatus.DEGRADED)
        failing = sum(1 for h in self.service_health.values() if h.status in [ServiceStatus.FAILING, ServiceStatus.DOWN])
        
        overall = "healthy" if failing == 0 and degraded == 0 else \
                  "degraded" if failing == 0 else "critical"
        
        return {
            "overall_status": overall,
            "services": {
                "total": total,
                "healthy": healthy,
                "degraded": degraded,
                "failing": failing
            },
            "uptime_percentage": round(healthy / total * 100, 1) if total > 0 else 100
        }


failover_engine = FailoverEngine()


def google_calendar_fallback(*args, **kwargs):
    """Fallback when Google Calendar is unavailable."""
    return {
        "message": "Calendar temporarily unavailable. Appointment queued for scheduling.",
        "queued": True,
        "fallback_active": True
    }


def twilio_fallback(*args, **kwargs):
    """Fallback when Twilio is unavailable."""
    return {
        "message": "Call/SMS queued for delivery when service resumes.",
        "queued": True,
        "fallback_active": True
    }


def openai_fallback(*args, **kwargs):
    """Fallback when OpenAI is unavailable."""
    return {
        "response": "I apologize, but I'm experiencing technical difficulties. Please hold while I connect you with a team member, or leave a message and we'll call you back shortly.",
        "fallback_active": True
    }


failover_engine.register_fallback("google_calendar", google_calendar_fallback)
failover_engine.register_fallback("twilio_voice", twilio_fallback)
failover_engine.register_fallback("twilio_sms", twilio_fallback)
failover_engine.register_fallback("openai_chat", openai_fallback)
failover_engine.register_fallback("openai_realtime", openai_fallback)
