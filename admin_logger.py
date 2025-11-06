"""
Simple logging system for Lightning API Admin Dashboard
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Any
from flask import request

class APILogger:
    def __init__(self, log_file='api_logs.json'):
        self.log_file = log_file
        self.ensure_log_file()
    
    def ensure_log_file(self):
        """Create log file if it doesn't exist"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                json.dump([], f)
    
    def log_request(self, method: str, path: str, status_code: int, 
                   duration_ms: float, user: str = None, error: str = None):
        """Log an API request"""
        try:
            # Read existing logs
            with open(self.log_file, 'r') as f:
                logs = json.load(f)
        except:
            logs = []
        
        # Add new log entry
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'method': method,
            'path': path,
            'status_code': status_code,
            'duration': round(duration_ms, 2),
            'user': user,
            'error': error,
            'ip': request.remote_addr if request else None
        }
        
        logs.append(log_entry)
        
        # Keep only last 1000 logs to prevent file from growing too large
        if len(logs) > 1000:
            logs = logs[-1000:]
        
        # Save logs
        try:
            with open(self.log_file, 'w') as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            print(f"Error saving logs: {e}")
    
    def get_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent logs"""
        try:
            with open(self.log_file, 'r') as f:
                logs = json.load(f)
            
            # Return most recent logs first
            return logs[-limit:][::-1]
        except:
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        try:
            with open(self.log_file, 'r') as f:
                logs = json.load(f)
        except:
            logs = []
        
        total_requests = len(logs)
        success_requests = len([log for log in logs if log['status_code'] < 400])
        error_requests = total_requests - success_requests
        unique_users = len(set(log.get('user', 'unknown') for log in logs if log.get('user')))
        
        # Recent activity (last 24 hours)
        from datetime import datetime, timedelta
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        
        recent_logs = []
        for log in logs:
            try:
                log_time = datetime.fromisoformat(log['timestamp'])
                if log_time > yesterday:
                    recent_logs.append(log)
            except:
                continue
        
        return {
            'total_requests': total_requests,
            'success_requests': success_requests,
            'error_requests': error_requests,
            'unique_users': unique_users,
            'recent_requests_24h': len(recent_logs),
            'average_response_time': round(sum(log.get('duration', 0) for log in logs) / max(len(logs), 1), 2)
        }
    
    def extract_user_from_request(self, request_obj) -> str:
        """Extract user identifier from request"""
        try:
            # Try to get from auth data if available
            if hasattr(request_obj, 'auth_data') and request_obj.auth_data:
                username = request_obj.auth_data.get('username')
                studio_name = request_obj.auth_data.get('studio_name')
                if username and studio_name:
                    return f"{username}:{studio_name}"
                elif username:
                    return username
            
            # Fallback to IP
            return request_obj.remote_addr or 'unknown'
        except:
            return 'unknown'

# Global logger instance
api_logger = APILogger()