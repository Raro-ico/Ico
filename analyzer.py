"""
Smart Analyzer Component
Monitors Instagram rate limits and adjusts behavior dynamically
"""

import time
import random
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from .config import config


@dataclass
class RateLimitEvent:
    """Records a rate limit event"""
    timestamp: float
    event_type: str  # 'success', 'rate_limit', 'error', 'timeout'
    delay_used: float
    response_time: float = 0.0
    error_message: str = ""


class SmartAnalyzer:
    """
    Intelligent rate limit analyzer that:
    1. Monitors Instagram responses and patterns
    2. Dynamically adjusts delays based on success/failure rates
    3. Detects rate limit patterns and adjusts accordingly
    4. Provides recommendations for optimal timing
    """
    
    def __init__(self):
        self.events: List[RateLimitEvent] = []
        self.current_delay = config.rate_limit.min_delay
        self.consecutive_successes = 0
        self.consecutive_failures = 0
        self.last_request_time = 0.0
        self.rate_limit_detected = False
        self.analysis_file = os.path.join(config.download.sessions_dir, "rate_analysis.json")
        
        # Load previous analysis if available
        self._load_analysis()
    
    def record_event(self, event_type: str, delay_used: float, 
                    response_time: float = 0.0, error_message: str = ""):
        """Record a rate limit event for analysis"""
        event = RateLimitEvent(
            timestamp=time.time(),
            event_type=event_type,
            delay_used=delay_used,
            response_time=response_time,
            error_message=error_message
        )
        
        self.events.append(event)
        
        # Update counters based on event type
        if event_type == 'success':
            self.consecutive_successes += 1
            self.consecutive_failures = 0
            self.rate_limit_detected = False
        elif event_type in ['rate_limit', 'error', 'timeout']:
            self.consecutive_failures += 1
            self.consecutive_successes = 0
            if event_type == 'rate_limit':
                self.rate_limit_detected = True
        
        # Adjust delay dynamically
        self._adjust_delay()
        
        # Save analysis periodically
        if len(self.events) % 10 == 0:
            self._save_analysis()
    
    def get_next_delay(self) -> float:
        """Calculate the optimal delay for the next request"""
        base_delay = self.current_delay
        
        # Add randomization to avoid pattern detection
        jitter = random.uniform(0.8, 1.2)
        calculated_delay = base_delay * jitter
        
        # Additional delay if rate limit was recently detected
        if self.rate_limit_detected:
            calculated_delay *= 2.0
        
        # Ensure we don't exceed maximum delay
        return min(calculated_delay, config.rate_limit.max_dynamic_delay)
    
    def should_take_batch_break(self, items_processed: int) -> bool:
        """Determine if a longer batch break is needed"""
        return (items_processed > 0 and 
                items_processed % config.rate_limit.batch_size == 0)
    
    def get_batch_delay(self) -> float:
        """Get delay duration for batch breaks"""
        base_delay = config.rate_limit.batch_delay
        
        # Increase batch delay if we're seeing rate limits
        if self.rate_limit_detected:
            return base_delay * 1.5
        
        # Decrease if we're having consistent success
        if self.consecutive_successes > 20:
            return base_delay * 0.8
        
        return base_delay
    
    def get_status_report(self) -> Dict:
        """Generate a status report of current rate limiting situation"""
        recent_events = [e for e in self.events if e.timestamp > time.time() - 3600]  # Last hour
        
        if not recent_events:
            return {
                "status": "no_data",
                "message": "No recent activity to analyze",
                "current_delay": self.current_delay,
                "rate_limit_detected": False
            }
        
        success_rate = len([e for e in recent_events if e.event_type == 'success']) / len(recent_events)
        avg_delay = sum(e.delay_used for e in recent_events) / len(recent_events)
        
        if self.rate_limit_detected:
            status = "rate_limited"
            message = "Rate limiting detected - using conservative delays"
        elif success_rate > 0.9:
            status = "optimal"
            message = "Operating at optimal speed"
        elif success_rate > 0.7:
            status = "cautious"
            message = "Some issues detected - using moderate delays"
        else:
            status = "problematic"
            message = "High failure rate - using maximum delays"
        
        return {
            "status": status,
            "message": message,
            "success_rate": success_rate,
            "current_delay": self.current_delay,
            "avg_delay": avg_delay,
            "consecutive_successes": self.consecutive_successes,
            "consecutive_failures": self.consecutive_failures,
            "rate_limit_detected": self.rate_limit_detected,
            "events_last_hour": len(recent_events)
        }
    
    def _adjust_delay(self):
        """Dynamically adjust delay based on recent events"""
        if self.consecutive_successes >= 5:
            # We're doing well, can reduce delay slightly
            self.current_delay *= config.rate_limit.success_reduction
            self.current_delay = max(self.current_delay, config.rate_limit.min_delay)
        
        elif self.consecutive_failures >= 2:
            # Having issues, increase delay
            self.current_delay *= config.rate_limit.failure_increase
            self.current_delay = min(self.current_delay, config.rate_limit.max_dynamic_delay)
        
        # Special handling for rate limits
        if self.rate_limit_detected and self.consecutive_failures >= 1:
            self.current_delay = min(config.rate_limit.max_dynamic_delay, self.current_delay * 2)
    
    def _save_analysis(self):
        """Save analysis data to file"""
        try:
            analysis_data = {
                "current_delay": self.current_delay,
                "consecutive_successes": self.consecutive_successes,
                "consecutive_failures": self.consecutive_failures,
                "rate_limit_detected": self.rate_limit_detected,
                "last_updated": time.time(),
                "recent_events": [asdict(e) for e in self.events[-100:]]  # Keep last 100 events
            }
            
            with open(self.analysis_file, 'w') as f:
                json.dump(analysis_data, f, indent=2)
        
        except Exception as e:
            print(f"⚠️  Warning: Could not save analysis data: {e}")
    
    def _load_analysis(self):
        """Load previous analysis data"""
        try:
            if os.path.exists(self.analysis_file):
                with open(self.analysis_file, 'r') as f:
                    data = json.load(f)
                
                # Only load recent data (less than 24 hours old)
                if time.time() - data.get('last_updated', 0) < 86400:
                    self.current_delay = data.get('current_delay', config.rate_limit.min_delay)
                    self.consecutive_successes = data.get('consecutive_successes', 0)
                    self.consecutive_failures = data.get('consecutive_failures', 0)
                    self.rate_limit_detected = data.get('rate_limit_detected', False)
                    
                    # Load recent events
                    recent_events = data.get('recent_events', [])
                    self.events = [RateLimitEvent(**event) for event in recent_events]
        
        except Exception as e:
            print(f"⚠️  Warning: Could not load previous analysis data: {e}")
    
    def wait_with_progress(self, delay: float, reason: str = "Rate limiting"):
        """Wait with a progress indicator and enforce global rate limiting"""
        # Enforce minimum spacing from last request
        if self.last_request_time > 0:
            time_since_last = time.time() - self.last_request_time
            min_spacing = config.rate_limit.min_delay
            
            if time_since_last < min_spacing:
                additional_delay = min_spacing - time_since_last
                delay = max(delay, additional_delay)
        
        if delay <= 0:
            self.last_request_time = time.time()
            return
        
        print(f"\n⏳ {reason}: waiting {delay:.1f} seconds...")
        
        # Show progress for longer delays
        if delay > 5:
            start_time = time.time()
            while time.time() - start_time < delay:
                elapsed = time.time() - start_time
                remaining = delay - elapsed
                progress = elapsed / delay * 100
                
                # Simple progress bar
                bar_length = 30
                filled_length = int(bar_length * progress / 100)
                bar = '█' * filled_length + '-' * (bar_length - filled_length)
                
                print(f"\r⏳ [{bar}] {progress:.1f}% - {remaining:.1f}s remaining", end="", flush=True)
                time.sleep(1)
                
                if remaining <= 0:
                    break
            print()  # New line after progress
        else:
            time.sleep(delay)
        
        self.last_request_time = time.time()