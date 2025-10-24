"""
Stateless authentication for Lightning-API v2
No sessions required - pass credentials with each request
Supports file upload, JSON, headers, and query params dynamically
"""
import time
import json
from datetime import datetime
from flask import request, jsonify
from lightning_sdk import Studio, User
from functools import wraps

# Cache studios to avoid recreating them for every request
STUDIO_CACHE = {}
CACHE_TTL = 300  # 5 minutes

def get_studio_from_auth(auth_data):
    """Get studio instance from authentication data with caching"""
    studio_name = auth_data.get('studio_name')
    teamspace = auth_data.get('teamspace')
    username = auth_data.get('username')
    lightning_user_id = auth_data.get('lightning_user_id')
    lightning_api_key = auth_data.get('lightning_api_key')
    create_ok = auth_data.get('create_ok', False)  # Default False - don't auto-create
    
    # Check required fields
    if not all([studio_name, teamspace, username]):
        return None, "Missing authentication fields: studio_name, teamspace, username"
    
    if not all([lightning_user_id, lightning_api_key]):
        return None, "Missing Lightning AI credentials: lightning_user_id, lightning_api_key"
    
    # Create cache key including user credentials
    cache_key = f"{lightning_user_id}:{teamspace}:{username}:{studio_name}"
    current_time = time.time()
    
    # Check cache
    if cache_key in STUDIO_CACHE:
        cached_data = STUDIO_CACHE[cache_key]
        if current_time - cached_data['timestamp'] < CACHE_TTL:
            return cached_data['studio'], None
    
    # Create new studio instance with user-specific credentials
    try:
        import os
        
        # Temporarily set user-specific environment variables
        original_user_id = os.environ.get('LIGHTNING_USER_ID')
        original_api_key = os.environ.get('LIGHTNING_API_KEY')
        
        # Set user-specific credentials
        os.environ['LIGHTNING_USER_ID'] = lightning_user_id
        os.environ['LIGHTNING_API_KEY'] = lightning_api_key
        
        try:
            # Follow Lightning AI SDK documentation - use 'name' parameter, not positional
            studio = Studio(
                name=studio_name,
                teamspace=teamspace,
                user=username,
                create_ok=create_ok
            )
            
            # Cache the studio with user credentials
            STUDIO_CACHE[cache_key] = {
                'studio': studio,
                'user_id': lightning_user_id,
                'api_key': lightning_api_key,
                'timestamp': current_time
            }
            
            # Clean old cache entries
            cleanup_cache()
            
            return studio, None
            
        finally:
            # Restore original environment variables
            if original_user_id is not None:
                os.environ['LIGHTNING_USER_ID'] = original_user_id
            else:
                os.environ.pop('LIGHTNING_USER_ID', None)
                
            if original_api_key is not None:
                os.environ['LIGHTNING_API_KEY'] = original_api_key
            else:
                os.environ.pop('LIGHTNING_API_KEY', None)
        
    except Exception as e:
        error_msg = str(e)
        # Check if it's a studio not found error and suggest create_ok
        if "studio" in error_msg.lower() and ("not found" in error_msg.lower() or "does not exist" in error_msg.lower()):
            return None, f"Studio '{studio_name}' not found. Add 'create_ok': true to your auth to create it automatically. Error: {error_msg}"
        return None, f"Failed to authenticate with Lightning AI: {error_msg}"

def cleanup_cache():
    """Remove expired entries from cache"""
    current_time = time.time()
    expired_keys = [
        key for key, data in STUDIO_CACHE.items()
        if current_time - data['timestamp'] > CACHE_TTL
    ]
    for key in expired_keys:
        del STUDIO_CACHE[key]

def extract_auth_from_file():
    """Extract authentication data from uploaded JSON file"""
    if 'auth_file' not in request.files:
        return None, None
    
    file = request.files['auth_file']
    if file.filename == '':
        return None, None
    
    try:
        # Read file content directly from memory
        file_content = file.read().decode('utf-8')
        auth_data = json.loads(file_content)
        
        # Validate required fields
        required_fields = ['studio_name', 'teamspace', 'username', 'lightning_user_id', 'lightning_api_key']
        missing_fields = [field for field in required_fields if not auth_data.get(field)]
        
        if missing_fields:
            return None, f"Missing required fields in auth file: {missing_fields}"
        
        return auth_data, None
        
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON in auth file: {str(e)}"
    except Exception as e:
        return None, f"Error reading auth file: {str(e)}"

def require_auth(func):
    """Decorator to require authentication - supports all methods dynamically"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_data = None
        error = None
        
        # Method 1: Try file upload first
        if 'auth_file' in request.files:
            auth_data, error = extract_auth_from_file()
            if error:
                return jsonify({"error": error}), 400
        
        # Method 2: JSON body authentication
        if not auth_data:
            data = request.get_json() or {}
            auth_data = data.get('auth', {})
        
        # Method 3: Header authentication  
        if not auth_data or not all(auth_data.get(k) for k in ['studio_name', 'teamspace', 'username']):
            auth_data = {
                'studio_name': request.headers.get('X-Studio-Name'),
                'teamspace': request.headers.get('X-Teamspace'),
                'username': request.headers.get('X-Username'),
                'lightning_user_id': request.headers.get('X-Lightning-User-ID'),
                'lightning_api_key': request.headers.get('X-Lightning-API-Key')
            }
        
        # Method 4: Query parameters (for GET requests)
        if not any(auth_data.values()):
            auth_data = {
                'studio_name': request.args.get('studio_name'),
                'teamspace': request.args.get('teamspace'),
                'username': request.args.get('username'),
                'lightning_user_id': request.args.get('lightning_user_id'),
                'lightning_api_key': request.args.get('lightning_api_key')
            }
        
        # Get studio instance with user-specific credentials
        studio, error = get_studio_from_auth(auth_data)
        if error:
            return jsonify({
                "error": error,
                "required_fields": [
                    "studio_name", "teamspace", "username", 
                    "lightning_user_id", "lightning_api_key"
                ],
                "auth_methods": [
                    "File: curl -F 'auth_file=@auth.json' /api/v2/status",
                    "JSON: {'auth': {'studio_name': '...', 'lightning_user_id': '...', 'lightning_api_key': '...'}}",
                    "Headers: X-Studio-Name, X-Lightning-User-ID, X-Lightning-API-Key",
                    "Query: ?studio_name=...&lightning_user_id=...&lightning_api_key=..."
                ]
            }), 401
        
        # Set user-specific environment for this request
        import os
        original_user_id = os.environ.get('LIGHTNING_USER_ID')
        original_api_key = os.environ.get('LIGHTNING_API_KEY')
        
        os.environ['LIGHTNING_USER_ID'] = auth_data['lightning_user_id']
        os.environ['LIGHTNING_API_KEY'] = auth_data['lightning_api_key']
        
        try:
            # Add to request context
            request.studio = studio
            request.auth_data = auth_data
            
            return func(*args, **kwargs)
        finally:
            # Restore original environment
            if original_user_id is not None:
                os.environ['LIGHTNING_USER_ID'] = original_user_id
            else:
                os.environ.pop('LIGHTNING_USER_ID', None)
                
            if original_api_key is not None:
                os.environ['LIGHTNING_API_KEY'] = original_api_key
            else:
                os.environ.pop('LIGHTNING_API_KEY', None)
    
    return wrapper

def require_multi_auth(func):
    """Decorator for multi-studio operations"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        data = request.get_json() or {}
        
        # Support both single studio and multiple studios
        studios_auth = data.get('studios', [])
        if not studios_auth:
            # Single studio mode
            auth_data = data.get('auth', {})
            if not auth_data:
                return jsonify({
                    "error": "Authentication required",
                    "format": {
                        "single_studio": {"auth": {"studio_name": "...", "teamspace": "...", "username": "..."}},
                        "multi_studio": {"studios": [{"studio_name": "...", "teamspace": "...", "username": "...", "alias": "..."}]}
                    }
                }), 401
            
            studio, error = get_studio_from_auth(auth_data)
            if error:
                return jsonify({"error": error}), 401
            
            request.studios = {"default": studio}
            request.default_studio = "default"
        else:
            # Multi-studio mode
            studios = {}
            for studio_config in studios_auth:
                alias = studio_config.get('alias', studio_config.get('studio_name', 'unnamed'))
                studio, error = get_studio_from_auth(studio_config)
                if error:
                    return jsonify({"error": f"Studio '{alias}': {error}"}), 401
                studios[alias] = studio
            
            request.studios = studios
            request.default_studio = list(studios.keys())[0] if studios else None
        
        return func(*args, **kwargs)
    
    return wrapper

def require_lightning_auth_only(func):
    """Decorator that only requires Lightning AI credentials (no studio info needed)"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        auth_data = None
        error = None
        
        # Method 1: Try file upload first
        if 'auth_file' in request.files:
            file = request.files['auth_file']
            if file.filename != '':
                try:
                    file_content = file.read().decode('utf-8')
                    auth_data = json.loads(file_content)
                except (json.JSONDecodeError, Exception) as e:
                    return jsonify({"error": f"Error reading auth file: {str(e)}"}), 400
        
        # Method 2: JSON body authentication
        if not auth_data:
            data = request.get_json() or {}
            auth_data = data.get('auth', {})
        
        # Method 3: Header authentication  
        if not auth_data or not all(auth_data.get(k) for k in ['lightning_user_id', 'lightning_api_key']):
            auth_data = {
                'lightning_user_id': request.headers.get('X-Lightning-User-ID'),
                'lightning_api_key': request.headers.get('X-Lightning-API-Key')
            }
        
        # Method 4: Query parameters
        if not auth_data.get('lightning_user_id') or not auth_data.get('lightning_api_key'):
            auth_data.update({
                'lightning_user_id': request.args.get('lightning_user_id'),
                'lightning_api_key': request.args.get('lightning_api_key')
            })
        
        # Check required Lightning AI credentials only
        if not all([auth_data.get('lightning_user_id'), auth_data.get('lightning_api_key')]):
            return jsonify({
                "error": "Lightning AI credentials required",
                "required_fields": ["lightning_user_id", "lightning_api_key"],
                "auth_methods": [
                    "File: curl -F 'auth_file=@minimal_auth.json' /api/v2/list",
                    "JSON: {'auth': {'lightning_user_id': '...', 'lightning_api_key': '...'}}",
                    "Headers: X-Lightning-User-ID, X-Lightning-API-Key",
                    "Query: ?lightning_user_id=...&lightning_api_key=..."
                ]
            }), 401
        
        # Set user-specific environment for this request
        import os
        original_user_id = os.environ.get('LIGHTNING_USER_ID')
        original_api_key = os.environ.get('LIGHTNING_API_KEY')
        
        os.environ['LIGHTNING_USER_ID'] = auth_data['lightning_user_id']
        os.environ['LIGHTNING_API_KEY'] = auth_data['lightning_api_key']
        
        try:
            # Add credentials to request context
            request.auth_data = auth_data
            
            return func(*args, **kwargs)
        finally:
            # Restore original environment
            if original_user_id is not None:
                os.environ['LIGHTNING_USER_ID'] = original_user_id
            else:
                os.environ.pop('LIGHTNING_USER_ID', None)
                
            if original_api_key is not None:
                os.environ['LIGHTNING_API_KEY'] = original_api_key
            else:
                os.environ.pop('LIGHTNING_API_KEY', None)
    
    return wrapper