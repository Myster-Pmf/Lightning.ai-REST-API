# Lightning-API v2.0 ⚡

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/framework-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Lightning AI](https://img.shields.io/badge/power-Lightning--AI-792ee5.svg)](https://lightning.ai/)

**The most streamlined REST API for managing Lightning AI Studios.** 

While the official Lightning AI SDK is powerful, its documentation is often sparse and its methods are locked behind local Python environments. This project unlocks those hidden capabilities by converting the SDK's core features into a high-performance, stateless REST interface—perfect for automation, external integration, and cross-platform workflows.

---

## 📋 Table of Contents
- [✨ Key Features](#-key-features)
- [🎯 Quick Start](#-quick-start)
- [📁 Project Structure](#-project-structure)
- [🔐 Authentication](#-authentication)
- [📡 API Reference](#-api-reference)
- [💻 Detailed Usage Examples](#-detailed-usage-examples)
- [👥 Multi-User Support](#-multi-user-support)
- [📊 Admin Dashboard](#-admin-dashboard)
- [🐳 Deployment](#-deployment)

---

## ✨ Key Features

### 🚀 Management & Automation
- **Studio Lifecycle**: Seamlessly start, stop, and switch machine types (T4, L4, A100, etc.).
- **Smart Hardware Switching**: Use Lightning's native machine-switching without downtime.
- **Auto-Creation**: Option to automatically provision studios if they don't exist.

### 📁 Advanced File Operations
- **Stateless Transfers**: Upload and download files directly to/from your studio instances.
- **Remote Execution**: Run shell commands and Python scripts with real-time stdout/stderr capture.

### 🛡️ Enterprise Ready
- **Stateless Auth**: No sessions or cookies. Pass credentials via headers, JSON, or file uploads.
- **Multi-Tenant Safe**: complete credential isolation between concurrent users.
- **Admin Dashboard**: Built-in monitoring interface for request logging and health checks.

---

## 🎯 Quick Start

### 1. Prerequisites
- python 3.7+
- Lightning AI Account ([Get API Keys here](https://lightning.ai/settings))

### 2. Installation
```bash
git clone https://github.com/your-repo/Lightning-Api.git
cd Lightning-Api
pip install -r requirements.txt
```

### 3. Launch the Server
```bash
python app.py
```
Server starts at `http://localhost:5000`. Visit `http://localhost:5000/docs` for interactive info.

---

## 📁 Project Structure

```text
Lightning-Api/
├── app.py              # Application Entry Point
├── admin_routes.py     # Admin Dashboard Logic
├── admin_logger.py     # Unified Request Logging
├── api/                # Core API Logic
│   ├── auth_v2.py      # Stateless Auth Middleware
│   ├── routes_v2.py    # Endpoint Definitions
│   └── machines.py     # Machine Type Specs
├── templates/          # Web Interface
│   └── admin.html      # Dashboard UI
├── examples/           # Client Snapshots
├── Dockerfile          # Container Configuration
├── Procfile            # Cloud Deployment Spec
├── requirements.txt    # Dependencies
└── DEPLOYMENT.md       # Production Guides
```


---

## 🔐 Authentication

Lightning-API is stateless. Every request requires **5 authentication fields**:

| Field | Description | Example |
|-------|-------------|---------|
| `studio_name` | Lightning AI studio name | `"my-awesome-studio"` |
| `teamspace` | Lightning AI teamspace | `"my-team"` |
| `username` | Lightning AI username | `"john-doe"` |
| `lightning_user_id` | Your Lightning AI User ID | `"0123...cdef"` |
| `lightning_api_key` | Your Lightning AI API Key | `"sk-...def"` |

### 4 Authentication Methods

#### 1. 🔥 **File Upload** (Recommended)
```bash
curl -F "auth_file=@auth.json" http://localhost:5000/api/v2/status
```

#### 2. **JSON Body**
```bash
curl -X POST http://localhost:5000/api/v2/status \
  -H "Content-Type: application/json" \
  -d '{
    "auth": {
      "studio_name": "my-studio",
      "teamspace": "my-team",
      "username": "my-user",
      "lightning_user_id": "0123...",
      "lightning_api_key": "sk-..."
    }
  }'
```

#### 3. **Headers**
```bash
curl -H "X-Studio-Name: my-studio" \
     -H "X-Teamspace: my-team" \
     -H "X-Username: my-user" \
     -H "X-Lightning-User-ID: 0123..." \
     -H "X-Lightning-API-Key: sk-..." \
     http://localhost:5000/api/v2/status
```

#### 4. **Query Parameters**
```bash
curl "http://localhost:5000/api/v2/status?studio_name=my-studio&teamspace=my-team&username=my-user..."
```

---

## 📡 API Reference

### Studio Management
| Endpoint | Method | Description |
|:--- |:--- |:--- |
| `/api/v2/status` | `POST` | Get current studio status and uptime |
| `/api/v2/start` | `POST` | Start studio (supports `machine_type`) |
| `/api/v2/stop` | `POST` | Stop the studio server |
| `/api/v2/switch-machine`| `POST` | Seamless hardware transition |
| `/api/v2/create` | `POST` | Provision a new studio instance |

### Workload & Files
| Endpoint | Method | Description |
|:--- |:--- |:--- |
| `/api/v2/execute` | `POST` | Run shell/python commands |
| `/api/v2/upload` | `POST` | Upload file to studio |
| `/api/v2/download/<path>`| `GET` | Retrieve file from studio |
| `/api/v2/files` | `GET` | List remote directory contents |

### Account Utilities
| Endpoint | Method | Description |
|:--- |:--- |:--- |
| `/api/v2/balance` | `GET` | Get account credit balance |
| `/api/v2/list` | `GET` | List all resources (users, studios) |
| `/api/machine-types` | `GET` | Live pricing and specifications |

---

## 💻 Detailed Usage Examples

### Using `curl` (Comprehensive)

```bash
# Check account balance
curl -F "auth_file=@minimal_auth.json" http://localhost:5000/api/v2/balance

# Start studio with specific GPU
curl -F "auth_file=@auth.json" -F "machine_type=T4" http://localhost:5000/api/v2/start

# Execute command on studio
curl -F "auth_file=@auth.json" -F "command=python train.py" http://localhost:5000/api/v2/execute

# Upload script to a specific path
curl -F "auth_file=@auth.json" -F "file=@local_script.py" -F "remote_path=scripts/run.py" http://localhost:5000/api/v2/upload

# Download result
curl -F "auth_file=@auth.json" http://localhost:5000/api/v2/download/output.txt -o result.txt
```

### Using Python

```python
import requests

auth = {
    "studio_name": "my-studio",
    "teamspace": "my-team", 
    "username": "my-user",
    "lightning_user_id": "...",
    "lightning_api_key": "..."
}

# Start studio
response = requests.post('http://localhost:5000/api/v2/start', 
                        json={"auth": auth, "machine_type": "GPU"})

# Execute command
response = requests.post('http://localhost:5000/api/v2/execute', 
                        json={"auth": auth, "command": "python script.py"})
print(response.json()['stdout'])

# Upload file
with open('data.csv', 'rb') as f:
    requests.post('http://localhost:5000/api/v2/upload', 
                 files={'auth_file': open('auth.json', 'rb'), 'file': f})
```

---

## 👥 Multi-User Support

Each user maintains their own Lightning AI credentials and studio access:

```bash
# Alice starts her GPU studio
curl -F "auth_file=@alice_auth.json,machine_type=GPU" http://localhost:5000/api/v2/start

# Bob starts his CPU studio simultaneously
curl -F "auth_file=@bob_auth.json,machine_type=CPU" http://localhost:5000/api/v2/start
```

### Security Features
- ✅ **Credential Isolation**: Each request uses only that user's credentials.
- ✅ **No Cross-User Access**: Users cannot access each other's studios.
- ✅ **Thread-Safe**: Multiple users can operate simultaneously.
- ✅ **Stateless**: No server-side user data storage.

---

## 📊 Admin Dashboard

Lightning-API comes with a built-in monitoring and documentation suite available at `/admin`.

- **Live Traffic**: Monitor API requests, status codes, and user attribution in real-time.
- **Analytics**: View core metrics like success rates, error counts, and unique user activity.
- **Interactive Documentation**: Copy-paste ready `curl` and JavaScript snippets for every endpoint.
- **Security**: Access is protected by the `ADMIN_PASSWORD` (set in your `.env`).

**Access**: [http://localhost:5000/admin](http://localhost:5000/admin)

---

## 🐳 Deployment

### Docker Build & Run
```bash
docker build -t lightning-api .
docker run -p 5000:5000 lightning-api
```

### Configuration
| Variable | Description | Default |
|:--- |:--- |:--- |
| `PORT` | Server listening port | `5000` |
| `DEBUG` | Enable Flask debug mode | `false` |
| `SECRET_KEY` | Flask session secret | `required` |

For detailed guides on production deployment (Heroku, AWS, GCP), see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
Built with ⚡ by the Lightning API Team.