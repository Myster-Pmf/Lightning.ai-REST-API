"""
Enhanced API routes for Lightning-API v2 with multi-studio support and async operations
"""
import os
import time
import tempfile
import threading
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file
from lightning_sdk import Machine, User
from lightning_sdk.api.studio_api import StudioApi
from lightning_sdk.teamspace import Teamspace
from werkzeug.utils import secure_filename

from .auth_v2 import require_auth, require_multi_auth, require_lightning_auth_only
from .machines import validate_machine_type, get_machine_suggestions, get_machine_info

api_v2_bp = Blueprint('api_v2', __name__)

# Store async operations and machine types
ASYNC_OPERATIONS = {}
STUDIO_MACHINE_TYPES = {}  # Track machine types for studios

def wait_for_studio_status(studio, target_status, max_wait=300, check_interval=10):
    """Wait for studio to reach target status"""
    elapsed = 0
    while elapsed < max_wait:
        try:
            current_status = str(studio.status).lower()
            if target_status.lower() in current_status:
                return True, current_status
            time.sleep(check_interval)
            elapsed += check_interval
        except Exception as e:
            return False, f"Error checking status: {e}"
    
    return False, f"Timeout waiting for status '{target_status}'"

@api_v2_bp.route('/status', methods=['GET', 'POST'])
@require_auth
def get_status():
    """Get studio status - supports both GET and POST"""
    try:
        studio = request.studio
        auth_data = request.auth_data
        
        # Get status
        status = str(studio.status)
        
        # Get both system uptime and studio uptime if running
        system_uptime = None
        studio_uptime = None
        uptime_error = None
        
        if 'running' in status.lower():
            # Get system uptime
            try:
                uptime_result = studio.run("uptime -p")
                if uptime_result:
                    system_uptime = str(uptime_result).strip()
            except Exception as e:
                uptime_error = str(e)
            
            # Calculate studio uptime from tracked start time
            studio_key = f"{auth_data['username']}:{auth_data['teamspace']}:{auth_data['studio_name']}"
            if studio_key in STUDIO_MACHINE_TYPES:
                try:
                    from datetime import timezone
                    started_at_str = STUDIO_MACHINE_TYPES[studio_key]['last_started']
                    started_at = datetime.fromisoformat(started_at_str.replace('Z', '+00:00'))
                    if started_at.tzinfo is None:
                        started_at = started_at.replace(tzinfo=timezone.utc)
                    
                    now = datetime.now(timezone.utc)
                    studio_duration = now - started_at
                    
                    # Format studio uptime
                    total_seconds = int(studio_duration.total_seconds())
                    hours, remainder = divmod(total_seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    
                    if hours > 0:
                        studio_uptime = f"up {hours} hours, {minutes} minutes"
                    elif minutes > 0:
                        studio_uptime = f"up {minutes} minutes"
                    else:
                        studio_uptime = f"up {seconds} seconds"
                        
                except Exception as e:
                    studio_uptime = f"Error calculating studio uptime: {e}"
        
        # Get working directory if running
        working_dir = None
        if 'running' in status.lower():
            try:
                pwd_result = studio.run("pwd")
                if pwd_result:
                    working_dir = str(pwd_result).strip()
            except:
                pass
        
        # Get machine type from tracked data or API
        machine_type = None
        studio_key = f"{auth_data['username']}:{auth_data['teamspace']}:{auth_data['studio_name']}"
        
        # First try to get from our tracked data
        if studio_key in STUDIO_MACHINE_TYPES:
            machine_type = STUDIO_MACHINE_TYPES[studio_key]['machine_type']
        
        # If not found, try to get from Lightning API
        if not machine_type:
            try:
                studio_api = StudioApi()
                client = getattr(studio_api, "_client", None)
                if client and auth_data.get('teamspace') and auth_data.get('username'):
                    teamspace = Teamspace(name=auth_data['teamspace'], user=auth_data['username'])
                    result = client.cloud_space_service_list_cloud_spaces(teamspace.id)
                    
                    if hasattr(result, 'to_dict'):
                        data = result.to_dict()
                        cloudspaces = data.get('cloudspaces', [])
                        for cs in cloudspaces:
                            # Match by display_name or name
                            if (cs.get('display_name') == auth_data['studio_name'] or 
                                cs.get('name') == auth_data['studio_name']):
                                
                                # Extract machine type from compute config
                                code_config = cs.get('code_config', {})
                                compute_config = code_config.get('compute_config', {})
                                machine_type = compute_config.get('name')
                                if machine_type:
                                    break
            except Exception as e:
                machine_type = None
        
        return jsonify({
            "success": True,
            "studio_name": auth_data['studio_name'],
            "status": status,
            "machine_type": machine_type or "",
            "system_uptime": system_uptime,
            "studio_uptime": studio_uptime,
            "uptime": system_uptime,  # Keep for backward compatibility
            "uptime_error": uptime_error,
            "working_directory": working_dir,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@api_v2_bp.route('/status/multi', methods=['POST'])
@require_multi_auth
def get_multi_status():
    """Get status for multiple studios"""
    try:
        studios = request.studios
        results = {}
        
        for alias, studio in studios.items():
            try:
                status = str(studio.status)
                
                # Get uptime if running
                uptime = None
                if 'running' in status.lower():
                    try:
                        uptime_result = studio.run("uptime -p")
                        if uptime_result:
                            uptime = str(uptime_result).strip()
                    except:
                        pass
                
                results[alias] = {
                    "success": True,
                    "status": status,
                    "uptime": uptime
                }
            except Exception as e:
                results[alias] = {
                    "success": False,
                    "error": str(e)
                }
        
        return jsonify({
            "success": True,
            "studios": results,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

def get_request_params():
    """Extract parameters from any request type (JSON, form, query)"""
    params = {}
    
    # Get from JSON body
    if request.is_json:
        data = request.get_json() or {}
        params.update(data)
    
    # Get from form data (for file uploads)
    if request.form:
        params.update(request.form.to_dict())
    
    # Get from query params
    if request.args:
        params.update(request.args.to_dict())
    
    return params

@api_v2_bp.route('/create', methods=['POST'])
@require_auth
def create_studio():
    """Create a new studio (requires create_ok=true in auth)"""
    try:
        studio = request.studio
        auth_data = request.auth_data
        
        # Check if create_ok was set to true
        if not auth_data.get('create_ok', False):
            return jsonify({
                "success": False,
                "error": "To create a studio, set 'create_ok': true in your authentication",
                "studio_name": auth_data['studio_name']
            }), 400
        
        # If we get here, studio was created successfully during auth
        status = str(studio.status)
        
        return jsonify({
            "success": True,
            "studio_name": auth_data['studio_name'],
            "message": f"Studio '{auth_data['studio_name']}' created successfully",
            "status": status,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@api_v2_bp.route('/start', methods=['POST'])
@require_auth
def start_studio():
    """Start studio with async support - supports all auth methods"""
    try:
        studio = request.studio
        auth_data = request.auth_data
        params = get_request_params()
        
        machine_type_str = params.get('machine_type', 'CPU')
        wait_for_ready = params.get('wait_for_ready', 'true').lower() == 'true'  # Default True
        timeout = int(params.get('timeout', '300'))
        
        # Validate and convert machine type
        if not validate_machine_type(machine_type_str):
            suggestions = get_machine_suggestions(machine_type_str)
            return jsonify({
                "success": False,
                "error": f"Invalid machine type: {machine_type_str}",
                "suggestions": suggestions,
                "all_types": get_machine_info(),
                "note": "See Lightning AI documentation for full machine type list"
            }), 400
        
        try:
            machine_type = getattr(Machine, machine_type_str)
        except AttributeError:
            return jsonify({
                "success": False,
                "error": f"Machine type '{machine_type_str}' not available in Lightning SDK",
                "note": "This may be a new machine type not yet supported"
            }), 400
        
        # Start studio
        operation_id = f"start_{int(time.time())}_{hash(auth_data['studio_name'])}"
        
        try:
            studio.start(machine_type)
            start_time = datetime.now()
            
            # Track machine type for this studio
            studio_key = f"{auth_data['username']}:{auth_data['teamspace']}:{auth_data['studio_name']}"
            STUDIO_MACHINE_TYPES[studio_key] = {
                'machine_type': machine_type_str,
                'started_at': start_time.isoformat(),
                'last_started': start_time.isoformat()
            }
            
            if wait_for_ready:
                # Wait for studio to be running
                success, final_status = wait_for_studio_status(studio, "running", timeout)
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                return jsonify({
                    "success": success,
                    "studio_name": auth_data['studio_name'],
                    "machine_type": machine_type_str,
                    "operation_id": operation_id,
                    "final_status": final_status,
                    "duration_seconds": duration,
                    "message": "Studio started and ready" if success else f"Studio start timeout: {final_status}",
                    "timestamp": datetime.now().isoformat()
                })
            else:
                # Async mode - start operation and return immediately
                def async_start():
                    try:
                        success, final_status = wait_for_studio_status(studio, "running", timeout)
                        end_time = datetime.now()
                        duration = (end_time - start_time).total_seconds()
                        
                        ASYNC_OPERATIONS[operation_id] = {
                            "success": success,
                            "final_status": final_status,
                            "duration_seconds": duration,
                            "completed_at": end_time.isoformat(),
                            "message": "Studio started and ready" if success else f"Studio start timeout: {final_status}"
                        }
                    except Exception as e:
                        ASYNC_OPERATIONS[operation_id] = {
                            "success": False,
                            "error": str(e),
                            "completed_at": datetime.now().isoformat()
                        }
                
                thread = threading.Thread(target=async_start)
                thread.daemon = True
                thread.start()
                
                return jsonify({
                    "success": True,
                    "studio_name": auth_data['studio_name'],
                    "machine_type": machine_type_str,
                    "operation_id": operation_id,
                    "message": "Studio start command sent",
                    "check_status_url": f"/api/v2/operation/{operation_id}",
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            return jsonify({
                "success": False,
                "studio_name": auth_data['studio_name'],
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@api_v2_bp.route('/switch-machine', methods=['POST'])
@require_auth
def switch_machine():
    """Switch studio to a different machine type without stopping"""
    try:
        studio = request.studio
        auth_data = request.auth_data
        params = get_request_params()
        
        new_machine_type_str = params.get('machine_type')
        if not new_machine_type_str:
            return jsonify({
                "success": False,
                "error": "No machine_type provided"
            }), 400
        
        # Check if studio is running
        status = str(studio.status)
        if 'running' not in status.lower():
            return jsonify({
                "success": False,
                "studio_name": auth_data['studio_name'],
                "error": f"Studio must be running to switch machine type (current status: {status})"
            }), 400
        
        # Get current machine type for comparison
        current_machine = None
        try:
            current_machine = str(studio.machine)
        except:
            current_machine = "unknown"
        
        # Validate new machine type
        if not validate_machine_type(new_machine_type_str):
            suggestions = get_machine_suggestions(new_machine_type_str)
            return jsonify({
                "success": False,
                "error": f"Invalid machine type: {new_machine_type_str}",
                "suggestions": suggestions,
                "all_types": get_machine_info(),
                "note": "See Lightning AI documentation for full machine type list"
            }), 400
        
        try:
            new_machine_type = getattr(Machine, new_machine_type_str)
        except AttributeError:
            return jsonify({
                "success": False,
                "error": f"Machine type '{new_machine_type_str}' not available in Lightning SDK",
                "note": "This may be a new machine type not yet supported"
            }), 400
        
        # Switch machine
        start_time = datetime.now()
        
        try:
            # Use Lightning SDK's built-in switch_machine method
            studio.switch_machine(new_machine_type)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Update our tracking
            studio_key = f"{auth_data['username']}:{auth_data['teamspace']}:{auth_data['studio_name']}"
            STUDIO_MACHINE_TYPES[studio_key] = {
                'machine_type': new_machine_type_str,
                'started_at': start_time.isoformat(),
                'last_started': start_time.isoformat(),
                'switched_from': current_machine,
                'switch_time': start_time.isoformat()
            }
            
            return jsonify({
                "success": True,
                "studio_name": auth_data['studio_name'],
                "message": f"Successfully switched from {current_machine} to {new_machine_type_str}",
                "previous_machine": current_machine,
                "new_machine": new_machine_type_str,
                "switch_duration_seconds": duration,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "studio_name": auth_data['studio_name'],
                "error": f"Failed to switch machine: {str(e)}",
                "current_machine": current_machine,
                "requested_machine": new_machine_type_str,
                "timestamp": datetime.now().isoformat()
            }), 500
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@api_v2_bp.route('/stop', methods=['POST'])
@require_auth
def stop_studio():
    """Stop studio with async support"""
    try:
        studio = request.studio
        auth_data = request.auth_data
        params = get_request_params()
        
        wait_for_stopped = params.get('wait_for_stopped', 'true').lower() == 'true'  # Default True
        timeout = int(params.get('timeout', '300'))
        
        operation_id = f"stop_{int(time.time())}_{hash(auth_data['studio_name'])}"
        
        try:
            studio.stop()
            start_time = datetime.now()
            
            if wait_for_stopped:
                # Wait for studio to stop
                success, final_status = wait_for_studio_status(studio, "stopped", timeout)
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                return jsonify({
                    "success": success,
                    "studio_name": auth_data['studio_name'],
                    "operation_id": operation_id,
                    "final_status": final_status,
                    "duration_seconds": duration,
                    "message": "Studio stopped" if success else f"Studio stop timeout: {final_status}",
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return jsonify({
                    "success": True,
                    "studio_name": auth_data['studio_name'],
                    "operation_id": operation_id,
                    "message": "Studio stop command sent",
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            return jsonify({
                "success": False,
                "studio_name": auth_data['studio_name'],
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@api_v2_bp.route('/operation/<operation_id>', methods=['GET'])
def get_operation_status(operation_id):
    """Get status of async operation"""
    if operation_id in ASYNC_OPERATIONS:
        return jsonify({
            "success": True,
            "operation_id": operation_id,
            "operation": ASYNC_OPERATIONS[operation_id],
            "timestamp": datetime.now().isoformat()
        })
    else:
        return jsonify({
            "success": False,
            "error": "Operation not found",
            "operation_id": operation_id
        }), 404

@api_v2_bp.route('/execute', methods=['POST'])
@require_auth
def execute_command():
    """Execute command on studio"""
    try:
        studio = request.studio
        auth_data = request.auth_data
        params = get_request_params()
        
        command = params.get('command')
        if not command:
            return jsonify({
                "success": False,
                "error": "No command provided"
            }), 400
        
        timeout = int(params.get('timeout', '300'))
        
        # Check if studio is running
        status = str(studio.status)
        if 'running' not in status.lower():
            return jsonify({
                "success": False,
                "studio_name": auth_data['studio_name'],
                "error": f"Studio is not running (status: {status})"
            }), 400
        
        start_time = time.time()
        
        # Execute command
        result = studio.run(command)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Parse result
        if hasattr(result, 'returncode'):
            return_code = result.returncode
            stdout = getattr(result, 'stdout', str(result))
            stderr = getattr(result, 'stderr', '')
        else:
            return_code = 0
            stdout = str(result) if result is not None else ""
            stderr = ''
        
        return jsonify({
            "success": return_code == 0,
            "studio_name": auth_data['studio_name'],
            "command": command,
            "return_code": return_code,
            "stdout": stdout,
            "stderr": stderr,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "command": data.get('command', '') if 'data' in locals() else '',
            "timestamp": datetime.now().isoformat()
        }), 500

@api_v2_bp.route('/upload', methods=['POST'])
@require_auth
def upload_file():
    """Upload file to studio"""
    try:
        studio = request.studio
        auth_data = request.auth_data
        
        # Check if studio is running
        status = str(studio.status)
        if 'running' not in status.lower():
            return jsonify({
                "success": False,
                "studio_name": auth_data['studio_name'],
                "error": f"Studio is not running (status: {status})"
            }), 400
        
        # Handle file upload - check for 'file' field (not auth_file)
        file_field = None
        for field_name in request.files:
            if field_name != 'auth_file':  # Skip auth file
                file_field = field_name
                break
        
        if not file_field or file_field not in request.files:
            return jsonify({
                "success": False,
                "error": "No file provided (use 'file' field, not 'auth_file')"
            }), 400
        
        file = request.files[file_field]
        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "No file selected"
            }), 400
        
        # Get remote path from form data
        remote_path = request.form.get('remote_path')
        if not remote_path:
            remote_path = secure_filename(file.filename)
        
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # Upload to studio
            studio.upload_file(temp_path, remote_path)
            
            # Clean up temp file
            os.unlink(temp_path)
            
            return jsonify({
                "success": True,
                "studio_name": auth_data['studio_name'],
                "message": f"File uploaded successfully to {remote_path}",
                "remote_path": remote_path,
                "filename": file.filename,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@api_v2_bp.route('/download/<path:file_path>', methods=['GET', 'POST'])
@require_auth
def download_file(file_path):
    """Download file from studio"""
    try:
        studio = request.studio
        auth_data = request.auth_data
        
        # Check if studio is running
        status = str(studio.status)
        if 'running' not in status.lower():
            return jsonify({
                "success": False,
                "studio_name": auth_data['studio_name'],
                "error": f"Studio is not running (status: {status})"
            }), 400
        
        # Create temp file for download
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        try:
            # Download from studio
            studio.download_file(file_path, temp_path)
            
            # Get filename for download
            filename = os.path.basename(file_path)
            
            return send_file(
                temp_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/octet-stream'
            )
            
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return jsonify({
                "success": False,
                "studio_name": auth_data['studio_name'],
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@api_v2_bp.route('/files', methods=['GET', 'POST'])
@require_auth
def list_files():
    """List files in studio directory"""
    try:
        studio = request.studio
        auth_data = request.auth_data
        
        # Check if studio is running
        status = str(studio.status)
        if 'running' not in status.lower():
            return jsonify({
                "success": False,
                "studio_name": auth_data['studio_name'],
                "error": f"Studio is not running (status: {status})"
            }), 400
        
        # Get directory path from any source
        params = get_request_params()
        path = params.get('path', '.')
        
        # List files using ls command
        command = f"ls -la '{path}' 2>/dev/null || ls -la ."
        result = studio.run(command)
        
        if not result:
            return jsonify({
                "success": False,
                "studio_name": auth_data['studio_name'],
                "error": "Could not list files"
            }), 500
        
        output = str(result)
        files = []
        
        # Parse ls output
        lines = output.strip().split('\n')
        for line in lines[1:]:  # Skip first line (total)
            line = line.strip()
            if not line or line.startswith('total'):
                continue
            
            parts = line.split()
            if len(parts) >= 9:
                permissions = parts[0]
                size = parts[4]
                name = ' '.join(parts[8:])
                
                # Skip . and ..
                if name in ['.', '..']:
                    continue
                
                file_type = 'directory' if permissions.startswith('d') else 'file'
                
                files.append({
                    "name": name,
                    "type": file_type,
                    "size": size,
                    "permissions": permissions
                })
        
        return jsonify({
            "success": True,
            "studio_name": auth_data['studio_name'],
            "path": path,
            "files": files,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500
@api_v2_bp.route('/list', methods=['GET', 'POST'])
@require_lightning_auth_only
def list_all_resources():
    """List all available resources using Lightning API like lightning_cli.py"""
    try:
        auth_data = request.auth_data
        
        # Initialize Studio API like in lightning_cli.py
        studio_api = StudioApi()
        client = getattr(studio_api, "_client", None)
        if not client:
            return jsonify({
                "success": False,
                "error": "Failed to initialize Lightning client"
            }), 500
        
        # Get user info like in lightning_cli.py
        try:
            user_profile = client.auth_service_get_user()
            user_info = {
                "id": getattr(user_profile, 'id', auth_data.get('lightning_user_id')),
                "username": getattr(user_profile, 'username', auth_data.get('username', 'unknown')),
                "first_name": getattr(user_profile, 'first_name', ''),
                "last_name": getattr(user_profile, 'last_name', ''),
                "email": getattr(user_profile, 'email', '')
            }
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Failed to get user info: {str(e)}",
                "note": "Check your Lightning AI credentials"
            }), 401
        
        # Get all teamspaces for this user
        teamspaces_info = []
        studios_by_teamspace = {}
        
        try:
            teamspaces = user.teamspaces
            
            for teamspace in teamspaces:
                teamspace_data = {
                    "name": teamspace.name,
                    "id": getattr(teamspace, 'id', 'unknown'),
                    "studios": []
                }
                
                # Get studios in this teamspace
                try:
                    studios = teamspace.studios if hasattr(teamspace, 'studios') else []
                    studio_list = []
                    
                    for studio in studios:
                        try:
                            studio_info = {
                                "name": studio.name,
                                "id": getattr(studio, 'id', 'unknown'),
                                "status": str(studio.status) if hasattr(studio, 'status') else 'unknown',
                                "machine_type": getattr(studio, 'machine_type', 'unknown'),
                                "created_at": getattr(studio, 'created_at', 'unknown')
                            }
                            studio_list.append(studio_info)
                        except Exception as e:
                            studio_list.append({
                                "name": getattr(studio, 'name', 'unknown'),
                                "error": f"Could not get studio info: {str(e)}"
                            })
                    
                    teamspace_data["studios"] = studio_list
                    teamspace_data["studio_count"] = len(studio_list)
                    
                except Exception as e:
                    teamspace_data["studios_error"] = f"Could not list studios: {str(e)}"
                    teamspace_data["studio_count"] = 0
                
                teamspaces_info.append(teamspace_data)
                studios_by_teamspace[teamspace.name] = teamspace_data["studios"]
                
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Failed to get teamspaces: {str(e)}",
                "user_info": user_info
            }), 500
        
        # Summary statistics
        total_studios = sum(len(studios) for studios in studios_by_teamspace.values())
        running_studios = 0
        stopped_studios = 0
        
        for studios in studios_by_teamspace.values():
            for studio in studios:
                if isinstance(studio, dict) and "status" in studio:
                    if "running" in studio["status"].lower():
                        running_studios += 1
                    elif "stopped" in studio["status"].lower():
                        stopped_studios += 1
        
        # Compile response
        response = {
            "success": True,
            "user": user_info,
            "summary": {
                "total_teamspaces": len(teamspaces_info),
                "total_studios": total_studios,
                "running_studios": running_studios,
                "stopped_studios": stopped_studios,
                "other_status_studios": total_studios - running_studios - stopped_studios
            },
            "teamspaces": teamspaces_info,
            "studios_by_teamspace": studios_by_teamspace,
            "timestamp": datetime.now().isoformat(),
            "note": "This endpoint lists all resources accessible with your Lightning AI credentials"
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to list resources: {str(e)}",
            "timestamp": datetime.now().isoformat(),
            "note": "Make sure your Lightning AI credentials are valid"
        }), 500

@api_v2_bp.route('/list/studios', methods=['GET', 'POST'])
@require_lightning_auth_only  
def list_studios_only():
    """List only studios across all teamspaces using Lightning API like lightning_cli.py"""
    try:
        auth_data = request.auth_data
        
        # Initialize Studio API like in lightning_cli.py
        studio_api = StudioApi()
        client = getattr(studio_api, "_client", None)
        if not client:
            return jsonify({
                "success": False,
                "error": "Failed to initialize Lightning client"
            }), 500
        
        # Get user profile first
        try:
            user_profile = client.auth_service_get_user()
            username = auth_data.get('username') or getattr(user_profile, 'username', 'unknown')
        except Exception as e:
            username = auth_data.get('username', 'unknown')
        
        all_studios = []
        teamspace_count = 0
        
        # For now, use the default teamspace from auth or try to get studios directly
        teamspace_name = auth_data.get('teamspace', 'default')
        
        try:
            teamspace = Teamspace(name=teamspace_name, user=username)
            project_id = teamspace.id
            teamspace_count = 1
            
            # Get studios using the API like in lightning_cli.py
            result = client.cloud_space_service_list_cloud_spaces(project_id)
            
            if hasattr(result, 'to_dict'):
                data = result.to_dict()
                cloudspaces = data.get('cloudspaces', [])
                
                for studio in cloudspaces:
                    try:
                        # Extract machine type like in lightning_cli.py
                        code_config = studio.get('code_config', {})
                        compute_config = code_config.get('compute_config', {})
                        machine_type = compute_config.get('name', 'unknown')
                        
                        # Format state
                        state = studio.get('state', 'Unknown').replace('CLOUD_SPACE_STATE_', '').lower()
                        
                        studio_info = {
                            "name": studio.get('display_name', studio.get('name', 'unknown')),
                            "teamspace": teamspace_name,
                            "status": state,
                            "machine_type": machine_type,
                            "id": studio.get('id', 'unknown'),
                            "created_at": studio.get('created_at', 'unknown'),
                            "number_of_files": studio.get('number_of_files', 0),
                            "total_size_bytes": studio.get('total_size_bytes', 0)
                        }
                        all_studios.append(studio_info)
                    except Exception as e:
                        all_studios.append({
                            "name": studio.get('display_name', 'unknown'),
                            "teamspace": teamspace_name,
                            "error": f"Could not get studio details: {str(e)}"
                        })
                        
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Failed to access teamspace '{teamspace_name}': {str(e)}",
                "note": "Make sure teamspace name and username are correct"
            }), 500
        
        return jsonify({
            "success": True,
            "username": username,
            "teamspace": teamspace_name,
            "total_teamspaces": teamspace_count,
            "total_studios": len(all_studios),
            "studios": all_studios,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to list studios: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500

def map_to_lightning_sdk_name(family, gpu_count, display_name):
    """Map machine family and GPU count to Lightning SDK machine name"""
    # Normalize inputs
    family = str(family).strip()
    gpu_count = int(gpu_count) if gpu_count else 0
    display_name = str(display_name).lower()
    
    # T4 machines
    if family == 'T4':
        if gpu_count == 1:
            return 'T4'
        elif gpu_count == 4:
            return 'T4_X_4'
    
    # L4 machines  
    elif family == 'L4':
        if gpu_count == 1:
            return 'L4' 
        elif gpu_count == 4:
            return 'L4_X_4'
        elif gpu_count == 8:
            return 'L4_X_8'
    
    # CPU machines
    elif family == 'CPU':
        if 'small' in display_name:
            return 'CPU_SMALL'
        else:
            return 'CPU'
    
    # Data prep machines
    elif family == 'DATA-PREP':
        if 'max' in display_name:
            return 'DATA_PREP_MAX'
        elif 'ultra' in display_name:
            return 'DATA_PREP_ULTRA'
        else:
            return 'DATA_PREP'
    
    # A100 machines
    elif family == 'A100':
        if gpu_count == 8:
            return 'A100_X_8'
    
    # H100 machines
    elif family == 'H100':
        if gpu_count == 8:
            return 'H100_X_8'
    
    # H200 machines (future)
    elif family == 'H200':
        if gpu_count == 8:
            return 'H200_X_8'  # Note: Not in current SDK but may be added
    
    # L40S maps to L40 in SDK
    elif family == 'L40S':
        if gpu_count == 1:
            return 'L40'
        elif gpu_count == 4:
            return 'L40_X_4'
        elif gpu_count == 8:
            return 'L40_X_8'
    
    # A10G machines
    elif family == 'A10G':
        if gpu_count == 1:
            return 'A10G'
        elif gpu_count == 4:
            return 'A10G_X_4'
        elif gpu_count == 8:
            return 'A10G_X_8'
    
    return None  # No mapping found

@api_v2_bp.route('/machine-types', methods=['GET', 'POST'])
@require_lightning_auth_only
def get_machine_types():
    """Get machine types and pricing with Lightning SDK mapping"""
    try:
        auth_data = request.auth_data
        
        # Initialize Studio API like in lightning_cli.py
        studio_api = StudioApi()
        client = getattr(studio_api, "_client", None)
        if not client:
            return jsonify({
                "success": False,
                "error": "Failed to initialize Lightning client"
            }), 500
        
        # Get machine pricing using the same method as lightning_cli.py
        try:
            accelerators = client.cluster_service_list_default_cluster_accelerators()
            if hasattr(accelerators, 'to_dict'):
                raw_machines = accelerators.to_dict().get('accelerator', [])
                
                # Format machine information with SDK mapping
                machines = []
                sdk_mapping = {}
                
                for machine in raw_machines:
                    resources = machine.get('resources', {})
                    memory_mb = int(resources.get('memory_mb', 0))
                    memory_gb = memory_mb // 1024 if memory_mb else 0
                    cost = machine.get('cost', 0)
                    spot_price = machine.get('spot_price', 0)
                    savings_pct = ((cost - spot_price) / cost * 100) if cost > 0 else 0
                    
                    family = machine.get('family', '')
                    gpu_count = resources.get('gpu', 0)
                    display_name = machine.get('display_name', 'Unknown')
                    
                    # Map to Lightning SDK name
                    sdk_name = map_to_lightning_sdk_name(family, gpu_count, display_name)
                    
                    machine_info = {
                        'name': display_name,
                        'lightning_sdk_name': sdk_name,
                        'family': family,
                        'instance_id': machine.get('instance_id', ''),
                        'provider': machine.get('provider', ''),
                        'cost_per_hour': cost,
                        'spot_price_per_hour': spot_price,
                        'savings_percentage': savings_pct,
                        'cpu_cores': resources.get('cpu', 0),
                        'memory_gb': memory_gb,
                        'gpu_count': gpu_count,
                        'gpu_type': resources.get('gpu_type', ''),
                        'availability_seconds': machine.get('available_in_seconds', 'N/A'),
                        'available_zones': len(machine.get('available_zones', [])),
                        'enabled': machine.get('enabled', False),
                        'tier_restricted': machine.get('is_tier_restricted', False),
                        'out_of_capacity': machine.get('out_of_capacity', False)
                    }
                    machines.append(machine_info)
                    
                    # Build SDK mapping for easy lookup
                    if sdk_name:
                        if sdk_name not in sdk_mapping:
                            sdk_mapping[sdk_name] = []
                        sdk_mapping[sdk_name].append({
                            'instance_id': machine.get('instance_id', ''),
                            'cost_per_hour': cost,
                            'display_name': display_name
                        })
                
                # Sort by cost like lightning_cli.py
                machines = sorted(machines, key=lambda x: x['cost_per_hour'])
                
                # Get unique SDK names for easy reference
                available_sdk_names = list(set(m['lightning_sdk_name'] for m in machines if m['lightning_sdk_name']))
                available_sdk_names.sort()
                
                return jsonify({
                    "success": True,
                    "total_machines": len(machines),
                    "machines": machines,
                    "sdk_mapping": sdk_mapping,
                    "available_sdk_names": available_sdk_names,
                    "usage_note": "Use 'lightning_sdk_name' values when starting studios with /api/v2/start",
                    "timestamp": datetime.now().isoformat()
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Failed to retrieve machine data from Lightning API"
                }), 500
                
        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"Failed to fetch machine pricing: {str(e)}"
            }), 500
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to get machine types: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500

@api_v2_bp.route('/balance', methods=['GET', 'POST'])
@require_lightning_auth_only
def get_balance():
    """Get balance information like lightning_cli.py"""
    try:
        auth_data = request.auth_data
        
        # Initialize Studio API like in lightning_cli.py
        studio_api = StudioApi()
        client = getattr(studio_api, "_client", None)
        if not client:
            return jsonify({
                "success": False,
                "error": "Failed to initialize Lightning client"
            }), 500
        
        data = {}
        
        # User balance
        try:
            user_balance = client.billing_service_get_user_balance()
            data['user_balance'] = user_balance.to_dict() if user_balance and hasattr(user_balance, 'to_dict') else None
        except Exception as e:
            data['user_balance'] = {'error': str(e)}
        
        # User profile
        try:
            user_profile = client.auth_service_get_user()
            data['user_profile'] = user_profile.to_dict() if user_profile and hasattr(user_profile, 'to_dict') else None
        except Exception as e:
            data['user_profile'] = {'error': str(e)}
        
        # Subscription
        try:
            subscription = client.billing_service_get_billing_subscription()
            data['subscription'] = subscription.to_dict() if subscription and hasattr(subscription, 'to_dict') else None
        except Exception as e:
            data['subscription'] = {'error': str(e)}
        
        # Teamspace balance if configured
        teamspace_name = auth_data.get('teamspace')
        username = auth_data.get('username')
        
        if teamspace_name and username:
            try:
                teamspace = Teamspace(name=teamspace_name, user=username)
                project_id = teamspace.id
                
                balance_result = client.billing_service_get_project_balance(project_id)
                
                data['teamspace'] = {
                    'name': teamspace.name,
                    'project_id': project_id,
                    'balance': balance_result.to_dict() if balance_result and hasattr(balance_result, 'to_dict') else None
                }
            except Exception as e:
                data['teamspace'] = {'error': str(e)}
        
        # Create summary only response like lightning_cli.py
        summary = {}
        
        # Personal balance
        user_balance = data.get('user_balance', {})
        if user_balance and 'error' not in user_balance:
            summary['personal_balance'] = user_balance.get('balance', 0)
            summary['total_spent'] = user_balance.get('total_spent', 0)
        
        # Teamspace balance
        teamspace = data.get('teamspace', {})
        if teamspace and 'error' not in teamspace and teamspace.get('balance'):
            balance_info = teamspace['balance']
            summary['teamspace_balance'] = balance_info.get('balance', 0)
            summary['teamspace_name'] = teamspace['name']
        
        # Subscription
        subscription = data.get('subscription', {})
        if subscription and 'error' not in subscription:
            summary['plan_name'] = subscription.get('name', 'Unknown')
            features = subscription.get('features', [])
            included_credits = next((f['limit'] for f in features if f.get('key') == 'included_credits'), 0)
            summary['included_credits'] = included_credits
        
        # Return only summary like lightning_cli.py
        return jsonify({
            "success": True,
            "balance": summary,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to get balance: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500
