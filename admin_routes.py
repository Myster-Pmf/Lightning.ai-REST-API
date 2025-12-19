"""
Admin routes for Lightning API Dashboard
"""
from flask import Blueprint, render_template, jsonify, request, session, redirect, url_for
from admin_logger import api_logger

admin_bp = Blueprint('admin', __name__)

# Admin password from environment variable
import os
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'lightning123')

@admin_bp.route('/admin')
def admin_dashboard():
    """Main admin dashboard"""
    return render_template('admin.html', admin_password=ADMIN_PASSWORD)

@admin_bp.route('/admin/api/stats')
def get_stats():
    """Get API usage statistics"""
    try:
        stats = api_logger.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/api/logs')
def get_logs():
    """Get recent API logs"""
    try:
        limit = request.args.get('limit', 50, type=int)
        logs = api_logger.get_logs(limit=limit)
        return jsonify({'logs': logs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/api/clear-logs', methods=['POST'])
def clear_logs():
    """Clear all logs (admin only)"""
    try:
        # Check password in request
        password = request.json.get('password') if request.is_json else request.form.get('password')
        if password != ADMIN_PASSWORD:
            return jsonify({'error': 'Invalid password'}), 403
        
        # Clear logs by writing empty array
        import json
        with open(api_logger.log_file, 'w') as f:
            json.dump([], f)
        
        return jsonify({'success': True, 'message': 'Logs cleared successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/health')
def admin_health():
    """Health check for admin interface"""
    return jsonify({
        'status': 'healthy',
        'admin_interface': 'active',
        'logging': 'enabled'
    })