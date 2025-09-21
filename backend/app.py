#!/usr/bin/env python3
"""
Flask Backend API for Enhanced Terminal Command Engine - CORS Fixed
"""

from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import json
import uuid
import threading
import time
from datetime import datetime
import os
import sys

# Import your terminal engine
try:
    from terminal_engine import TerminalEngine
except ImportError:
    print("Error: terminal_engine.py not found. Please save the enhanced terminal code as terminal_engine.py")
    sys.exit(1)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# SIMPLIFIED CORS CONFIGURATION - This fixes the duplicate header issue
CORS(app, 
     origins=['http://localhost:3000', 'http://127.0.0.1:3000', 'http://localhost:5173', 'http://127.0.0.1:5173'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization'],
     supports_credentials=True)

# Initialize SocketIO
socketio = SocketIO(
    app, 
    cors_allowed_origins=['http://localhost:3000', 'http://127.0.0.1:3000', 'http://localhost:5173', 'http://127.0.0.1:5173'],
    async_mode='threading',
    logger=True,
    engineio_logger=True
)

# Store terminal instances for different sessions
terminal_sessions = {}
system_stats_cache = {}

class TerminalSession:
    """Wrapper class to manage individual terminal sessions."""
    
    def __init__(self, session_id):
        self.session_id = session_id
        self.terminal = TerminalEngine()
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        
    def execute_command(self, command):
        """Execute command and capture output."""
        import io
        import sys
        from contextlib import redirect_stdout, redirect_stderr
        
        self.last_activity = datetime.now()
        
        # Capture stdout and stderr
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        
        try:
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                success = self.terminal.execute_single_command(command)
            
            stdout_content = stdout_buffer.getvalue()
            stderr_content = stderr_buffer.getvalue()
            
            # Combine outputs
            output = ''
            if stdout_content:
                output += stdout_content
            if stderr_content:
                if output:
                    output += '\n'
                output += stderr_content
            
            return {
                'success': success,
                'output': output.strip() if output else 'Command executed successfully',
                'current_directory': self.terminal.current_directory,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'output': f'Error executing command: {str(e)}',
                'current_directory': self.terminal.current_directory,
                'timestamp': datetime.now().isoformat()
            }

def get_or_create_session(session_id=None):
    """Get existing session or create new one."""
    if not session_id:
        session_id = str(uuid.uuid4())
    
    if session_id not in terminal_sessions:
        terminal_sessions[session_id] = TerminalSession(session_id)
    
    return terminal_sessions[session_id]

def cleanup_old_sessions():
    """Clean up inactive sessions."""
    current_time = datetime.now()
    sessions_to_remove = []
    
    for session_id, terminal_session in terminal_sessions.items():
        # Remove sessions inactive for more than 1 hour
        if (current_time - terminal_session.last_activity).seconds > 3600:
            sessions_to_remove.append(session_id)
    
    for session_id in sessions_to_remove:
        del terminal_sessions[session_id]

def update_system_stats():
    """Background task to update system statistics."""
    try:
        import psutil
    except ImportError:
        print("Warning: psutil not installed. System stats will not be available.")
        return
    
    while True:
        try:
            stats = {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory': {
                    'total': psutil.virtual_memory().total,
                    'available': psutil.virtual_memory().available,
                    'percent': psutil.virtual_memory().percent,
                    'used': psutil.virtual_memory().used
                },
                'disk': {
                    'total': psutil.disk_usage('/').total,
                    'used': psutil.disk_usage('/').used,
                    'free': psutil.disk_usage('/').free,
                    'percent': psutil.disk_usage('/').percent
                },
                'timestamp': datetime.now().isoformat()
            }
            
            system_stats_cache['current'] = stats
            
            # Broadcast to all connected clients
            socketio.emit('system_stats', stats)
            
        except Exception as e:
            print(f"Error updating system stats: {e}")
        
        time.sleep(2)  # Update every 2 seconds

# Start background threads
stats_thread = threading.Thread(target=update_system_stats, daemon=True)
stats_thread.start()

def cleanup_thread_func():
    while True:
        cleanup_old_sessions()
        time.sleep(300)  # Cleanup every 5 minutes

cleanup_thread = threading.Thread(target=cleanup_thread_func, daemon=True)
cleanup_thread.start()

# REMOVED DUPLICATE CORS HANDLERS - Flask-CORS handles this automatically

@app.route('/api/terminal/new', methods=['POST'])
def create_terminal_session():
    """Create a new terminal session."""
    try:
        session_id = str(uuid.uuid4())
        terminal_session = get_or_create_session(session_id)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'current_directory': terminal_session.terminal.current_directory,
            'message': 'Terminal session created successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/terminal/execute', methods=['POST'])
def execute_command():
    """Execute a command in the terminal."""
    try:
        data = request.get_json()
        
        if not data or 'command' not in data:
            return jsonify({
                'success': False,
                'error': 'Command is required'
            }), 400
        
        command = data['command'].strip()
        session_id = data.get('session_id')
        
        if not command:
            return jsonify({
                'success': False,
                'error': 'Empty command'
            }), 400
        
        # Get or create terminal session
        terminal_session = get_or_create_session(session_id)
        
        # Execute command
        result = terminal_session.execute_command(command)
        
        # Add session_id to response
        result['session_id'] = terminal_session.session_id
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/terminal/history/<session_id>', methods=['GET'])
def get_command_history(session_id):
    """Get command history for a session."""
    try:
        if session_id not in terminal_sessions:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        terminal_session = terminal_sessions[session_id]
        
        return jsonify({
            'success': True,
            'history': terminal_session.terminal.command_history,
            'total_commands': len(terminal_session.terminal.command_history)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/system/stats', methods=['GET'])
def get_system_stats():
    """Get current system statistics."""
    try:
        if 'current' in system_stats_cache:
            return jsonify({
                'success': True,
                'stats': system_stats_cache['current']
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Stats not available yet'
            }), 503
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/system/processes', methods=['GET'])
def get_processes():
    """Get list of running processes."""
    try:
        import psutil
        
        limit = int(request.args.get('limit', 20))
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                if len(processes) >= limit:
                    break
                    
                processes.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'cpu_percent': proc.info['cpu_percent'] or 0,
                    'memory_percent': proc.info['memory_percent'] or 0
                })
                
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        return jsonify({
            'success': True,
            'processes': processes,
            'total_shown': len(processes)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/terminal/sessions', methods=['GET'])
def get_active_sessions():
    """Get list of active terminal sessions."""
    try:
        sessions_info = []
        
        for session_id, terminal_session in terminal_sessions.items():
            sessions_info.append({
                'session_id': session_id,
                'created_at': terminal_session.created_at.isoformat(),
                'last_activity': terminal_session.last_activity.isoformat(),
                'current_directory': terminal_session.terminal.current_directory,
                'command_count': len(terminal_session.terminal.command_history)
            })
        
        return jsonify({
            'success': True,
            'sessions': sessions_info,
            'total_sessions': len(sessions_info)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/debug', methods=['GET', 'POST', 'OPTIONS'])
def debug_headers():
    """Debug endpoint to see request headers and CORS setup."""
    return jsonify({
        'method': request.method,
        'headers': dict(request.headers),
        'origin': request.headers.get('Origin'),
        'host': request.headers.get('Host'),
        'user_agent': request.headers.get('User-Agent'),
        'message': 'Debug info for CORS troubleshooting - CORS should now work correctly'
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.1',
        'active_sessions': len(terminal_sessions),
        'async_mode': socketio.async_mode,
        'cors_status': 'configured'
    })

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print(f'Client connected: {request.sid}')
    emit('connection_established', {
        'message': 'Connected to terminal server',
        'timestamp': datetime.now().isoformat(),
        'async_mode': socketio.async_mode
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    print(f'Client disconnected: {request.sid}')

@socketio.on('execute_command')
def handle_command_execution(data):
    """Handle real-time command execution via WebSocket."""
    try:
        command = data.get('command', '').strip()
        session_id = data.get('session_id')
        
        if not command:
            emit('command_error', {'error': 'Empty command'})
            return
        
        # Get or create terminal session
        terminal_session = get_or_create_session(session_id)
        
        # Execute command
        result = terminal_session.execute_command(command)
        result['session_id'] = terminal_session.session_id
        
        # Emit result back to client
        emit('command_result', result)
        
    except Exception as e:
        emit('command_error', {'error': str(e)})

@socketio.on('request_stats')
def handle_stats_request():
    """Handle request for current system stats."""
    if 'current' in system_stats_cache:
        emit('system_stats', system_stats_cache['current'])
    else:
        emit('stats_error', {'error': 'Stats not available'})

# Error Handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

@app.errorhandler(400)
def bad_request(error):
    """Handle 400 errors."""
    return jsonify({
        'success': False,
        'error': 'Bad request'
    }), 400

# Development server configuration
if __name__ == '__main__':
    print("Starting Enhanced Terminal Backend Server with CORS Fixed...")
    print(f"Flask-SocketIO async mode: {socketio.async_mode}")
    print("CORS Configuration: Properly configured for frontend origins")
    print("Available endpoints:")
    print("  POST /api/terminal/new          - Create new terminal session")
    print("  POST /api/terminal/execute      - Execute command")
    print("  GET  /api/terminal/history/<id> - Get command history")
    print("  GET  /api/system/stats          - Get system statistics")
    print("  GET  /api/system/processes      - Get running processes")
    print("  GET  /api/terminal/sessions     - Get active sessions")
    print("  GET  /api/health                - Health check")
    print("\nWebSocket events:")
    print("  connect                         - Client connection")
    print("  disconnect                      - Client disconnection")
    print("  execute_command                 - Real-time command execution")
    print("  request_stats                   - Request system stats")
    print("\nServer running on http://localhost:8000")
    print("WebSocket available on ws://localhost:8000")
    
    # Run the application with threading mode
    port = int(os.environ.get('PORT', 8000))
    print(f"Starting server on port {port}")
    
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=port, 
        debug=True,
        use_reloader=False
    )