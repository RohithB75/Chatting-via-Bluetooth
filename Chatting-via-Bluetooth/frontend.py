from flask import Flask, render_template, request, jsonify
import subprocess
import threading
import time
import os
import sys
from datetime import datetime
import queue

app = Flask(__name__)

# Get the absolute path to the python-scripts directory
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'python-scripts')

# Use the same Python interpreter that's running this script
PYTHON_EXECUTABLE = sys.executable

# Global variables to track server and client status
server_process = None
client_process = None

# Store messages in memory (you might want to use a database in production)
messages = []

def read_process_output(process, is_server=True):
    while True:
        if process and process.poll() is None:
            try:
                output = process.stdout.readline().strip()
                if output:
                    print(f"Raw output: {output}")  # Debug print
                    if output.startswith("Client:"):
                        msg = output.replace("Client:", "").strip()
                        messages.append({
                            'text': msg,
                            'is_sent': not is_server,
                            'timestamp': time.time()
                        })
                        print(f"Added client message: {msg}")
                    elif output.startswith("Server:"):
                        msg = output.replace("Server:", "").strip()
                        messages.append({
                            'text': msg,
                            'is_sent': is_server,
                            'timestamp': time.time()
                        })
                        print(f"Added server message: {msg}")
                    elif output.startswith("You:"):
                        msg = output.replace("You:", "").strip()
                        messages.append({
                            'text': msg,
                            'is_sent': is_server,
                            'timestamp': time.time()
                        })
                        print(f"Added self message: {msg}")
            except Exception as e:
                print(f"Error reading output: {e}")
                break
        else:
            break

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run_script', methods=['POST'])
def run_script():
    global server_process, client_process
    script_name = request.form.get('script_name')
    
    try:
        if script_name == "server":
            if server_process is None or server_process.poll() is not None:
                server_process = subprocess.Popen(
                    [PYTHON_EXECUTABLE, os.path.join(SCRIPTS_DIR, 'server.py')],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                threading.Thread(target=read_process_output, args=(server_process, True), daemon=True).start()
                return jsonify({"status": "success", "message": "Server started successfully"})
            else:
                return jsonify({"status": "info", "message": "Server is already running"})

        elif script_name == "client":
            if client_process is None or client_process.poll() is not None:
                client_process = subprocess.Popen(
                    [PYTHON_EXECUTABLE, os.path.join(SCRIPTS_DIR, 'client.py')],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                threading.Thread(target=read_process_output, args=(client_process, False), daemon=True).start()
                return jsonify({"status": "success", "message": "Client started successfully"})
            else:
                return jsonify({"status": "info", "message": "Client is already running"})

    except Exception as e:
        print(f"Error starting script: {e}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/stop_script', methods=['POST'])
def stop_script():
    global server_process, client_process
    script_name = request.form.get('script_name')

    try:
        if script_name == "server" and server_process:
            server_process.terminate()
            server_process = None
            return jsonify({"status": "success", "message": "Server stopped"})
        elif script_name == "client" and client_process:
            client_process.terminate()
            client_process = None
            return jsonify({"status": "success", "message": "Client stopped"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

    return jsonify({"status": "info", "message": f"{script_name} is not running"})

@app.route('/update_messages', methods=['GET', 'POST'])
def update_messages():
    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return jsonify({"status": "error", "message": "No JSON data received"}), 400
            
            message = data.get('message')
            is_server = data.get('is_sent') == False  # True for server, False for client
            
            if not message or not isinstance(message, str):
                return jsonify({"status": "error", "message": "Invalid message format"}), 400
            
            # Send message to appropriate process
            target_process = server_process if is_server else client_process
            if target_process and target_process.poll() is None:
                try:
                    target_process.stdin.write(f"{message}\n")
                    target_process.stdin.flush()
                    print(f"Message sent to {'server' if is_server else 'client'}: {message}")
                    
                    # Add message to our list
                    messages.append({
                        'text': message,
                        'is_sent': not is_server,  # Flip is_sent for correct display
                        'timestamp': time.time()
                    })
                except Exception as e:
                    print(f"Error sending to process: {e}")
                    return jsonify({"status": "error", "message": str(e)}), 500
            
            return jsonify({"status": "success"})
        except Exception as e:
            print(f"Error in POST /update_messages: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500
    else:  # GET request
        try:
            # Sort messages by timestamp to ensure correct order
            sorted_messages = sorted(messages, key=lambda x: x['timestamp'])
            return jsonify({"status": "success", "messages": sorted_messages})
        except Exception as e:
            print(f"Error in GET /update_messages: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
