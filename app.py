"""
Lightning-API v2: Enhanced Flask REST API with stateless authentication
"""
import os
import time
from flask import Flask, request, g
from flask_cors import CORS
from dotenv import load_dotenv

# Import routes
from api.routes_v2 import api_v2_bp
from admin_routes import admin_bp
from admin_logger import api_logger

# Load environment variables
load_dotenv()

def create_app():
    """Create Flask application with both v1 and v2 APIs"""
    app = Flask(__name__)
    
    # Enable CORS for all routes
    CORS(app)
    
    # Configure Flask app
    app.secret_key = os.getenv('SECRET_KEY', 'lightning-api-secret-key-change-this')
    app.config['DEBUG'] = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Store active sessions for v1 compatibility
    app.config['ACTIVE_SESSIONS'] = {}
    
    # Register blueprints
    # V2 API (stateless with all auth methods)
    app.register_blueprint(api_v2_bp, url_prefix='/api/v2')
    app.register_blueprint(api_v2_bp, url_prefix='/api', name='api_default')  # Default to v2
    
    # Admin dashboard
    app.register_blueprint(admin_bp)
    
    # Request logging middleware
    @app.before_request
    def before_request():
        g.start_time = time.time()
    
    @app.after_request
    def after_request(response):
        try:
            # Calculate request duration
            duration = (time.time() - g.start_time) * 1000  # Convert to milliseconds
            
            # Only log API requests (not static files, admin interface, etc.)
            if request.path.startswith('/api/'):
                # Extract user info
                user = api_logger.extract_user_from_request(request)
                
                # Log the request
                api_logger.log_request(
                    method=request.method,
                    path=request.path,
                    status_code=response.status_code,
                    duration_ms=duration,
                    user=user,
                    error=None if response.status_code < 400 else f"HTTP {response.status_code}"
                )
        except Exception as e:
            # Don't let logging errors affect the API response
            print(f"Logging error: {e}")
        
        return response
    
    @app.route('/')
    def index():
        """Redirect to admin dashboard"""
        from flask import redirect, url_for
        return redirect(url_for('admin.admin_dashboard'))
    
    @app.route('/docs')
    def api_docs():
        """API information endpoint"""
        return {
            "name": "Lightning-API",
            "version": "2.0.0",
            "description": "REST API for Lightning AI Studio management",
            "api_versions": {
                "v2": {
                    "description": "Stateless API with multiple auth methods",
                    "auth_required": "Pass credentials with each request",
                    "base_path": "/api/v2"
                }
            },
            "admin_dashboard": "/admin",
            "endpoints": {
                "studio_management": {
                    "list_resources": "/api/v2/list",
                    "list_studios": "/api/v2/list/studios", 
                    "status": "/api/v2/status",
                    "create": "/api/v2/create",
                    "start": "/api/v2/start",
                    "stop": "/api/v2/stop"
                },
                "operations": {
                    "execute": "/api/v2/execute",
                    "upload": "/api/v2/upload",
                    "download": "/api/v2/download/<path>",
                    "files": "/api/v2/files"
                },
                "utility": {
                    "machine_types": "/api/machine-types",
                    "balance": "/api/v2/balance",
                    "health": "/health"
                }
            },
            "examples": {
                "v2_auth_methods": [
                    "Headers: X-Studio-Name, X-Teamspace, X-Username, X-Lightning-User-ID, X-Lightning-API-Key",
                    "JSON body: {'auth': {'studio_name': '...', 'teamspace': '...', 'username': '...', 'lightning_user_id': '...', 'lightning_api_key': '...'}}",
                    "Query params: ?studio_name=...&teamspace=...&username=...&lightning_user_id=...&lightning_api_key=..."
                ],
                "file_auth_methods": [
                    "Upload JSON file with credentials: curl -F 'auth_file=@auth.json' /api/file/status",
                    "Auth file format: {'studio_name': '...', 'teamspace': '...', 'username': '...', 'lightning_user_id': '...', 'lightning_api_key': '...'}"
                ]
            }
        }
    
    @app.route('/health')
    def health():
        """Health check endpoint"""
        return {"status": "healthy", "api": "Lightning-API", "version": "2.0.0"}
    
    @app.route('/api/machine-types')
    def get_machine_types():
        """Get available machine types with pricing from Lightning AI API"""
        try:
            from lightning_sdk.api.studio_api import StudioApi
            
            # Initialize Lightning API client
            studio_api = StudioApi()
            client = getattr(studio_api, "_client", None)
            if not client:
                # Fallback to basic machine types
                from api.machines import get_machine_info
                machine_info = get_machine_info()
                
                machine_types = []
                gpu_descriptions = {
                    "CPU": "CPU-only machine - $0.00/hr",
                    "T4": "NVIDIA T4 - Good for inference and light training",
                    "L4": "NVIDIA L4 - Balanced performance", 
                    "A10G": "NVIDIA A10G - High performance",
                    "A100": "NVIDIA A100 - Top performance (variant independent)",
                    "H100": "NVIDIA H100 - Latest generation",
                    "GPU": "Generic GPU machine",
                    "GPU_FAST": "Fast GPU machine"
                }
                
                for name, desc in gpu_descriptions.items():
                    machine_types.append({
                        "name": name,
                        "value": name,
                        "description": desc,
                        "category": "cpu" if name == "CPU" else "gpu",
                        "cost_per_hour": 0.0,
                        "pricing_available": False
                    })
                
                return {
                    "machine_types": machine_types,
                    "pricing_available": False,
                    "note": "Live pricing unavailable, showing basic machine types"
                }
            
            # Get machine types and pricing like lightning_cli.py
            try:
                accelerators_response = client.cluster_service_list_default_cluster_accelerators()
                
                # Handle response like lightning_cli.py does
                if hasattr(accelerators_response, 'to_dict'):
                    raw_data = accelerators_response.to_dict()
                    raw_machines = raw_data.get('accelerator', [])
                else:
                    raw_machines = []
                
                if not raw_machines:
                    return {
                        "machine_types": [],
                        "pricing_available": False,
                        "error": "No machine data available"
                    }
                
                machine_types = []
                for machine in raw_machines:
                    # Extract like lightning_cli.py format_machine_info
                    resources = machine.get('resources', {})
                    memory_mb = int(resources.get('memory_mb', 0))
                    memory_gb = memory_mb // 1024 if memory_mb else 0
                    cost = machine.get('cost', 0)
                    spot_price = machine.get('spot_price', 0)
                    savings_pct = ((cost - spot_price) / cost * 100) if cost > 0 else 0
                    
                    machine_info = {
                        'name': machine.get('display_name', 'Unknown'),
                        'value': machine.get('display_name', 'Unknown'),
                        'cost_per_hour': cost,
                        'spot_price_per_hour': spot_price,
                        'savings_percentage': round(savings_pct, 1),
                        'description': f"{resources.get('gpu_type', 'CPU')} - ${cost:.3f}/hr",
                        'category': "gpu" if resources.get('gpu', 0) > 0 else "cpu",
                        'cpu_cores': resources.get('cpu', 0),
                        'memory_gb': memory_gb,
                        'gpu_count': resources.get('gpu', 0),
                        'gpu_type': resources.get('gpu_type', ''),
                        'provider': machine.get('provider', ''),
                        'enabled': machine.get('enabled', False),
                        'tier_restricted': machine.get('is_tier_restricted', False),
                        'out_of_capacity': machine.get('out_of_capacity', False)
                    }
                    machine_types.append(machine_info)
                
                # Sort by cost
                machine_types = sorted(machine_types, key=lambda x: x['cost_per_hour'])
                
                return {
                    "success": True,
                    "machine_types": machine_types,
                    "pricing_available": True,
                    "total_machines": len(machine_types),
                    "note": "Live pricing from Lightning AI API"
                }
                
            except Exception as e:
                # Fallback on API error
                return {
                    "machine_types": [],
                    "pricing_available": False,
                    "error": f"Failed to get live pricing: {str(e)}"
                }
                
        except Exception as e:
            return {
                "machine_types": [],
                "pricing_available": False,
                "error": f"Machine types endpoint error: {str(e)}"
            }
    
    @app.route('/docs')
    def docs():
        """API documentation endpoint"""
        return {
            "documentation": "See README.md and API_DOCS.md",
            "examples": {
                "v2_status_check": {
                    "url": "/api/v2/status",
                    "method": "GET",
                    "auth": "?studio_name=my-studio&teamspace=my-team&username=my-user"
                },
                "v2_start_studio": {
                    "url": "/api/v2/start",
                    "method": "POST",
                    "body": {
                        "auth": {"studio_name": "my-studio", "teamspace": "my-team", "username": "my-user"},
                        "machine_type": "GPU",
                        "wait_for_ready": True
                    }
                },
                "v2_execute_command": {
                    "url": "/api/v2/execute",
                    "method": "POST",
                    "body": {
                        "auth": {"studio_name": "my-studio", "teamspace": "my-team", "username": "my-user"},
                        "command": "python my_script.py"
                    }
                }
            }
        }
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Lightning-API v2.0 on port {port}")
    print(f"V1 API (session-based): http://localhost:{port}/api/v1")
    print(f"V2 API (stateless): http://localhost:{port}/api/v2")
    print(f"Documentation: http://localhost:{port}/docs")
    app.run(host='0.0.0.0', port=port, debug=app.config['DEBUG'])