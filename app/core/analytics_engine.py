"""
Phase 9 - Analytics & Intelligence Engine
Business performance dashboard with predictive analytics.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import json


@dataclass
class PerformanceMetrics:
    total_calls: int = 0
    answered_calls: int = 0
    missed_calls: int = 0
    avg_call_duration: float = 0.0
    conversion_rate: float = 0.0
    appointments_booked: int = 0
    appointments_completed: int = 0
    revenue: float = 0.0
    avg_ticket: float = 0.0
    customer_satisfaction: float = 0.0


@dataclass
class TechnicianPerformance:
    technician_id: int
    technician_name: str
    jobs_completed: int = 0
    revenue_generated: float = 0.0
    avg_rating: float = 0.0
    on_time_rate: float = 0.0
    callback_rate: float = 0.0
    avg_job_duration: float = 0.0


@dataclass
class Prediction:
    metric: str
    current_value: float
    predicted_value: float
    confidence: float
    trend: str
    factors: List[str]
    recommendations: List[str]


@dataclass
class Insight:
    category: str
    title: str
    description: str
    impact: str
    priority: int
    action_items: List[str]
    data_points: Dict[str, Any]


class AnalyticsEngine:
    """Analytics and business intelligence engine."""
    
    def __init__(self):
        self.metrics_cache: Dict[str, Any] = {}
        self.cache_ttl = timedelta(minutes=15)
    
    def get_performance_metrics(
        self,
        business_id: int,
        start_date: datetime = None,
        end_date: datetime = None,
        calls: List[Dict] = None,
        appointments: List[Dict] = None
    ) -> PerformanceMetrics:
        """Calculate key performance metrics for a business."""
        start_date = start_date or datetime.now() - timedelta(days=30)
        end_date = end_date or datetime.now()
        calls = calls or []
        appointments = appointments or []
        
        total_calls = len(calls)
        answered = sum(1 for c in calls if c.get("outcome") != "missed")
        missed = sum(1 for c in calls if c.get("outcome") == "missed")
        
        call_durations = [c.get("duration_seconds", 0) for c in calls if c.get("duration_seconds")]
        avg_duration = sum(call_durations) / len(call_durations) if call_durations else 0
        
        appointments_booked = sum(
            1 for c in calls if c.get("outcome") == "appointment_booked"
        )
        
        conversion = (appointments_booked / total_calls * 100) if total_calls > 0 else 0
        
        completed_apts = sum(
            1 for a in appointments if a.get("status") == "completed"
        )
        
        revenues = [a.get("total_price", 0) for a in appointments if a.get("status") == "completed"]
        total_revenue = sum(revenues)
        avg_ticket = total_revenue / len(revenues) if revenues else 0
        
        ratings = [a.get("rating") for a in appointments if a.get("rating")]
        satisfaction = sum(ratings) / len(ratings) if ratings else 0
        
        return PerformanceMetrics(
            total_calls=total_calls,
            answered_calls=answered,
            missed_calls=missed,
            avg_call_duration=round(avg_duration, 1),
            conversion_rate=round(conversion, 1),
            appointments_booked=appointments_booked,
            appointments_completed=completed_apts,
            revenue=round(total_revenue, 2),
            avg_ticket=round(avg_ticket, 2),
            customer_satisfaction=round(satisfaction, 1)
        )
    
    def get_technician_performance(
        self,
        technicians: List[Dict],
        appointments: List[Dict],
        dispatch_logs: List[Dict] = None
    ) -> List[TechnicianPerformance]:
        """Analyze individual technician performance."""
        dispatch_logs = dispatch_logs or []
        performance = []
        
        for tech in technicians:
            tech_id = tech.get("id")
            tech_appointments = [
                a for a in appointments
                if a.get("technician_id") == tech_id
            ]
            
            completed = [a for a in tech_appointments if a.get("status") == "completed"]
            
            revenue = sum(a.get("total_price", 0) for a in completed)
            
            ratings = [a.get("rating") for a in completed if a.get("rating")]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0
            
            on_time_count = sum(1 for a in completed if a.get("was_on_time", True))
            on_time_rate = (on_time_count / len(completed) * 100) if completed else 100
            
            callbacks = sum(1 for a in completed if a.get("required_callback"))
            callback_rate = (callbacks / len(completed) * 100) if completed else 0
            
            durations = [a.get("actual_duration", 60) for a in completed]
            avg_duration = sum(durations) / len(durations) if durations else 60
            
            performance.append(TechnicianPerformance(
                technician_id=tech_id,
                technician_name=tech.get("name", "Unknown"),
                jobs_completed=len(completed),
                revenue_generated=round(revenue, 2),
                avg_rating=round(avg_rating, 1),
                on_time_rate=round(on_time_rate, 1),
                callback_rate=round(callback_rate, 1),
                avg_job_duration=round(avg_duration, 0)
            ))
        
        performance.sort(key=lambda x: x.revenue_generated, reverse=True)
        
        return performance
    
    def analyze_call_patterns(
        self,
        calls: List[Dict]
    ) -> Dict[str, Any]:
        """Analyze call patterns for optimization."""
        by_hour = defaultdict(int)
        by_day = defaultdict(int)
        by_outcome = defaultdict(int)
        by_service = defaultdict(int)
        
        for call in calls:
            call_time = call.get("start_time")
            if isinstance(call_time, str):
                try:
                    call_time = datetime.fromisoformat(call_time)
                except:
                    continue
            elif not call_time:
                continue
            
            by_hour[call_time.hour] += 1
            by_day[call_time.strftime("%A")] += 1
            
            outcome = call.get("outcome", "unknown")
            by_outcome[outcome] += 1
            
            service = call.get("service_type", "general")
            by_service[service] += 1
        
        peak_hour = max(by_hour.items(), key=lambda x: x[1])[0] if by_hour else 12
        peak_day = max(by_day.items(), key=lambda x: x[1])[0] if by_day else "Monday"
        
        return {
            "calls_by_hour": dict(by_hour),
            "calls_by_day": dict(by_day),
            "calls_by_outcome": dict(by_outcome),
            "calls_by_service": dict(by_service),
            "peak_hour": peak_hour,
            "peak_day": peak_day,
            "busiest_period": f"{peak_day}s around {peak_hour}:00"
        }
    
    def generate_predictions(
        self,
        historical_metrics: List[Dict],
        current_metrics: PerformanceMetrics
    ) -> List[Prediction]:
        """Generate predictive analytics."""
        predictions = []
        
        if len(historical_metrics) >= 4:
            recent_revenue = [m.get("revenue", 0) for m in historical_metrics[-4:]]
            trend = (recent_revenue[-1] - recent_revenue[0]) / recent_revenue[0] if recent_revenue[0] else 0
            
            predicted_revenue = current_metrics.revenue * (1 + trend)
            
            predictions.append(Prediction(
                metric="monthly_revenue",
                current_value=current_metrics.revenue,
                predicted_value=round(predicted_revenue, 2),
                confidence=0.75,
                trend="up" if trend > 0 else "down",
                factors=[
                    f"Based on {len(historical_metrics)} months of data",
                    f"Current trend: {trend*100:.1f}% month-over-month"
                ],
                recommendations=[
                    "Focus on high-value services to increase revenue" if trend < 0 else "Maintain current strategies"
                ]
            ))
        
        if current_metrics.conversion_rate > 0:
            if current_metrics.avg_call_duration < 60:
                predicted_conversion = current_metrics.conversion_rate * 0.9
                recommendations = ["Improve call scripts to increase engagement"]
            elif current_metrics.avg_call_duration > 180:
                predicted_conversion = current_metrics.conversion_rate * 1.1
                recommendations = ["Current engagement is strong"]
            else:
                predicted_conversion = current_metrics.conversion_rate
                recommendations = ["Consider follow-up automation"]
            
            predictions.append(Prediction(
                metric="conversion_rate",
                current_value=current_metrics.conversion_rate,
                predicted_value=round(predicted_conversion, 1),
                confidence=0.65,
                trend="up" if predicted_conversion > current_metrics.conversion_rate else "stable",
                factors=[
                    f"Avg call duration: {current_metrics.avg_call_duration}s",
                    f"Current conversion: {current_metrics.conversion_rate}%"
                ],
                recommendations=recommendations
            ))
        
        return predictions
    
    def generate_insights(
        self,
        metrics: PerformanceMetrics,
        call_patterns: Dict,
        tech_performance: List[TechnicianPerformance]
    ) -> List[Insight]:
        """Generate actionable business insights."""
        insights = []
        
        if metrics.missed_calls > metrics.answered_calls * 0.1:
            insights.append(Insight(
                category="operations",
                title="High Missed Call Rate",
                description=f"You're missing {metrics.missed_calls} calls, which is {metrics.missed_calls/(metrics.total_calls or 1)*100:.0f}% of total calls.",
                impact="Potential revenue loss of ${:.0f}".format(metrics.missed_calls * metrics.avg_ticket * 0.3),
                priority=1,
                action_items=[
                    "Enable after-hours AI answering",
                    "Set up missed call follow-up automation",
                    "Consider adding phone lines during peak hours"
                ],
                data_points={
                    "missed_calls": metrics.missed_calls,
                    "total_calls": metrics.total_calls,
                    "missed_rate": metrics.missed_calls / (metrics.total_calls or 1) * 100
                }
            ))
        
        peak_hour = call_patterns.get("peak_hour", 12)
        insights.append(Insight(
            category="scheduling",
            title=f"Peak Call Time: {peak_hour}:00",
            description=f"Your busiest time is around {peak_hour}:00 on {call_patterns.get('peak_day', 'weekdays')}.",
            impact="Optimize staffing for better coverage",
            priority=3,
            action_items=[
                f"Ensure full staffing from {peak_hour-1}:00 to {peak_hour+2}:00",
                "Schedule technician meetings outside peak hours",
                "Consider promotional offers for off-peak times"
            ],
            data_points=call_patterns.get("calls_by_hour", {})
        ))
        
        if tech_performance:
            top_tech = max(tech_performance, key=lambda x: x.revenue_generated)
            low_tech = min(tech_performance, key=lambda x: x.avg_rating) if len(tech_performance) > 1 else None
            
            insights.append(Insight(
                category="team",
                title=f"Top Performer: {top_tech.technician_name}",
                description=f"Generated ${top_tech.revenue_generated:.0f} with {top_tech.jobs_completed} jobs and {top_tech.avg_rating:.1f} star rating.",
                impact="Model behavior for team training",
                priority=4,
                action_items=[
                    "Recognize and reward top performer",
                    "Have them mentor newer technicians",
                    "Assign high-value jobs to maintain performance"
                ],
                data_points={
                    "revenue": top_tech.revenue_generated,
                    "jobs": top_tech.jobs_completed,
                    "rating": top_tech.avg_rating
                }
            ))
            
            if low_tech and low_tech.avg_rating < 4.0:
                insights.append(Insight(
                    category="team",
                    title=f"Training Opportunity: {low_tech.technician_name}",
                    description=f"Rating of {low_tech.avg_rating:.1f} is below team average. Callback rate: {low_tech.callback_rate:.0f}%.",
                    impact="Improve customer satisfaction",
                    priority=2,
                    action_items=[
                        "Schedule performance review",
                        "Provide additional training",
                        "Shadow top performer"
                    ],
                    data_points={
                        "rating": low_tech.avg_rating,
                        "callback_rate": low_tech.callback_rate
                    }
                ))
        
        if metrics.conversion_rate < 30:
            insights.append(Insight(
                category="sales",
                title="Low Conversion Rate",
                description=f"Only {metrics.conversion_rate:.0f}% of calls convert to appointments.",
                impact="Significant revenue opportunity",
                priority=1,
                action_items=[
                    "Review and improve call scripts",
                    "Implement AI quote generation",
                    "Add urgency offers for same-day service",
                    "Follow up on unconverted leads"
                ],
                data_points={
                    "conversion_rate": metrics.conversion_rate,
                    "potential_gain": (metrics.total_calls * 0.4 - metrics.appointments_booked) * metrics.avg_ticket
                }
            ))
        
        insights.sort(key=lambda x: x.priority)
        
        return insights
    
    def get_dashboard_summary(
        self,
        business_id: int,
        calls: List[Dict] = None,
        appointments: List[Dict] = None,
        technicians: List[Dict] = None
    ) -> Dict[str, Any]:
        """Get complete dashboard summary."""
        calls = calls or []
        appointments = appointments or []
        technicians = technicians or []
        
        metrics = self.get_performance_metrics(
            business_id,
            calls=calls,
            appointments=appointments
        )
        
        call_patterns = self.analyze_call_patterns(calls)
        
        tech_performance = self.get_technician_performance(
            technicians,
            appointments
        )
        
        insights = self.generate_insights(
            metrics,
            call_patterns,
            tech_performance
        )
        
        return {
            "metrics": {
                "total_calls": metrics.total_calls,
                "answered_calls": metrics.answered_calls,
                "missed_calls": metrics.missed_calls,
                "avg_call_duration": metrics.avg_call_duration,
                "conversion_rate": metrics.conversion_rate,
                "appointments_booked": metrics.appointments_booked,
                "appointments_completed": metrics.appointments_completed,
                "revenue": metrics.revenue,
                "avg_ticket": metrics.avg_ticket,
                "customer_satisfaction": metrics.customer_satisfaction
            },
            "call_patterns": call_patterns,
            "technician_performance": [
                {
                    "id": t.technician_id,
                    "name": t.technician_name,
                    "jobs": t.jobs_completed,
                    "revenue": t.revenue_generated,
                    "rating": t.avg_rating,
                    "on_time_rate": t.on_time_rate
                }
                for t in tech_performance[:5]
            ],
            "insights": [
                {
                    "category": i.category,
                    "title": i.title,
                    "description": i.description,
                    "priority": i.priority,
                    "actions": i.action_items
                }
                for i in insights[:5]
            ],
            "generated_at": datetime.now().isoformat()
        }


analytics_engine = AnalyticsEngine()
