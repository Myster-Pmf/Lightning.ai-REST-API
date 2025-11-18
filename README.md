# Lightning-API v2.0 ⚡

**The simplest REST API for managing Lightning AI Studios**

---

## 📋 Table of Contents
- [🎯 Quick Start](#-quick-start)
- [🚀 Features](#-features)  
- [🔧 Server Setup](#-server-setup)
- [🔐 Authentication](#-authentication)
- [📡 API Endpoints](#-api-endpoints)
- [💻 Usage Examples](#-usage-examples)
- [👥 Multi-User Support](#-multi-user-support)
- [🐳 Docker Deployment](#-docker-deployment)

---

## 🎯 Quick Start

### 1. Get your Lightning AI credentials
- Go to https://lightning.ai/ → Settings → API Keys
- Copy your **User ID** and **API Key**

### 2. Create auth file
```bash
cat > auth.json << EOF
{
  "studio_name": "your-studio-name",
  "teamspace": "your-teamspace", 
  "username": "your-username",
  "lightning_user_id": "your-lightning-user-id",
  "lightning_api_key": "your-lightning-api-key"
}
EOF
```

### 3. Start the server
```bash
git clone <repo>
cd Lightning-Api
pip install -r requirements.txt
python app_v2.py
```

### 4. Use the API
```bash
# Get status
curl -F "auth_file=@auth.json" http://localhost:5000/api/v2/status

# Start studio
curl -F "auth_file=@auth.json,machine_type=GPU" http://localhost:5000/api/v2/start

# Execute command
curl -F "auth_file=@auth.json,command=python script.py" http://localhost:5000/api/v2/execute
```

---

## 🚀 Features

✅ **Multiple Auth Methods**: File upload, JSON, headers, query params  
✅ **Multi-User Safe**: Each user has isolated Lightning AI credentials  
✅ **File Operations**: Upload, download, list files on studios  
✅ **Studio Management**: Start, stop, execute commands with progress tracking  
✅ **Smart Defaults**: `wait_for_ready=true`, sensible timeouts  
✅ **Production Ready**: Stateless, scalable, thread-safe  
✅ **Easy Integration**: Works with curl, Python, JavaScript, any HTTP client  

---

## 🔧 Server Setup

### Requirements
- Python 3.7+
- Lightning AI account and credentials

### Installation
```bash
# Clone repository
git clone <your-repo-url>
cd Lightning-Api

# Install dependencies
pip install -r requirements.txt

# Optional: Copy environment template
cp .env.example .env
# Edit .env with your default settings (optional)
```

### Running the Server
```bash
# Development
python app_v2.py

# Production with gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app_v2:app

# With custom port
PORT=8080 python app_v2.py

# With debug mode
DEBUG=true python app_v2.py
```

The server will be available at `http://localhost:5000`

### Health Check
```bash
curl http://localhost:5000/health
# Returns: {"status": "healthy", "api": "Lightning-API", "version": "2.0.0"}
```

---

## 🔐 Authentication

Every API call requires **5 authentication fields**:

| Field | Description | Example |
|-------|-------------|---------|
| `studio_name` | Lightning AI studio name | `"my-awesome-studio"` |
| `teamspace` | Lightning AI teamspace | `"my-team"` |
| `username` | Lightning AI username | `"john-doe"` |
| `lightning_user_id` | Your Lightning AI User ID | `"01234567-89ab-cdef-0123-456789abcdef"` |
| `lightning_api_key` | Your Lightning AI API Key | `"sk-1234567890abcdef..."` |

### Auth File Format
```json
{
  "studio_name": "my-awesome-studio",
  "teamspace": "my-team",
  "username": "my-username",
  "lightning_user_id": "01234567-89ab-cdef-0123-456789abcdef",
  "lightning_api_key": "sk-1234567890abcdef0123456789abcdef0123456789abcdef",
  "create_ok": false
}
```

**Important:** Set `"create_ok": true` only when you want to create new studios automatically. By default (`false`), the API will show a warning if the studio doesn't exist.

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
      "lightning_user_id": "01234567-89ab-cdef-0123-456789abcdef",
      "lightning_api_key": "sk-1234567890abcdef..."
    }
  }'
```

#### 3. **Headers**
```bash
curl -H "X-Studio-Name: my-studio" \
     -H "X-Teamspace: my-team" \
     -H "X-Username: my-user" \
     -H "X-Lightning-User-ID: 01234567-89ab-cdef-0123-456789abcdef" \
     -H "X-Lightning-API-Key: sk-1234567890abcdef..." \
     http://localhost:5000/api/v2/status
```

#### 4. **Query Parameters**
```bash
curl "http://localhost:5000/api/v2/status?studio_name=my-studio&teamspace=my-team&username=my-user&lightning_user_id=01234567-89ab-cdef-0123-456789abcdef&lightning_api_key=sk-1234567890abcdef..."
```

---

## 📡 API Endpoints

All endpoints support all 4 authentication methods. Default base URL: `/api/v2/`

### Account & Resource Management

#### `GET/POST /api/v2/balance`
Get account balance and spending information.

**Authentication:** Only `lightning_user_id` and `lightning_api_key` required (no studio info needed)

**Response:**
```json
{
  "success": true,
  "balance": {
    "personal_balance": 0.0,
    "total_spent": 60.66,
    "teamspace_balance": 12.86,
    "teamspace_name": "vision-model",
    "plan_name": "Free",
    "included_credits": 15
  },
  "timestamp": "2024-01-15T10:30:00"
}
```

#### `GET/POST /api/v2/list`
List all resources (users, teamspaces, studios) accessible with your Lightning AI credentials.

**Authentication:** Only `lightning_user_id` and `lightning_api_key` required

**Response:**
```json
{
  "success": true,
  "username": "john-doe",
  "teamspace": "my-team",
  "total_teamspaces": 1,
  "total_studios": 8,
  "studios": [
    {
      "name": "dev-studio",
      "teamspace": "my-team", 
      "status": "running",
      "machine_type": "cpu-4",
      "number_of_files": 25,
      "total_size_bytes": 1048576,
      "created_at": "2024-01-10T15:30:00"
    }
  ]
}
```

#### `GET/POST /api/v2/list/studios`
List only studios across all teamspaces with detailed information.

**Authentication:** Only `lightning_user_id` and `lightning_api_key` required

**Response:**
```json
{
  "success": true,
  "username": "john-doe",
  "teamspace": "my-team",
  "total_teamspaces": 1,
  "total_studios": 8,
  "studios": [
    {
      "name": "dev-studio",
      "teamspace": "my-team",
      "status": "running",
      "machine_type": "cpu-4",
      "id": "studio-123",
      "created_at": "2024-01-10T15:30:00",
      "number_of_files": 25,
      "total_size_bytes": 1048576
    },
    {
      "name": "prod-studio", 
      "teamspace": "my-team",
      "status": "stopped",
      "machine_type": "gpu-fast",
      "id": "studio-456",
      "created_at": "2024-01-08T09:15:00",
      "number_of_files": 50,
      "total_size_bytes": 2097152
    }
  ]
}
```

### Studio Management

#### `POST /api/v2/status`
Get current studio status and information.

**Parameters:** None

**Response:**
```json
{
  "success": true,
  "studio_name": "my-studio",
  "status": "running",
  "machine_type": "T4",
  "uptime": "up 2 hours, 30 minutes",
  "working_directory": "/teamspace/studios/my-studio",
  "timestamp": "2024-01-15T10:30:00"
}
```

#### `POST /api/v2/create`
Create a new studio (requires `create_ok: true` in authentication).

**Parameters:** None (uses auth data)

**Response:**
```json
{
  "success": true,
  "studio_name": "my-studio",
  "message": "Studio 'my-studio' created successfully",
  "status": "stopped",
  "timestamp": "2024-01-15T10:30:00"
}
```

#### `POST /api/v2/start`
Start studio with specified machine type (waits for ready by default).

**Parameters:**
- `machine_type` (optional): Lightning SDK machine names (default: `"CPU"`)
  - **CPU**: `"CPU"`, `"DATA_PREP"`, `"DATA_PREP_MAX"`
  - **Single GPU**: `"T4"`, `"L4"`, `"L40"`, `"A10G"`
  - **Multi GPU**: `"T4_X_4"`, `"L4_X_4"`, `"L4_X_8"`, `"A100_X_8"`, `"H100_X_8"`
- `wait_for_ready` (optional): `"true"` or `"false"` (default: `"true"`)
- `timeout` (optional): Timeout in seconds (default: `"300"`)

**Response:**
```json
{
  "success": true,
  "studio_name": "my-studio",
  "machine_type": "GPU",
  "final_status": "running",
  "duration_seconds": 45.2,
  "message": "Studio started and ready"
}
```

#### `POST /api/v2/switch-machine`
Switch studio to a different machine type without stopping (seamless transition).

**Parameters:**
- `machine_type` (required): New Lightning SDK machine name
  - **CPU**: `"CPU"`, `"DATA_PREP"`, `"DATA_PREP_MAX"`
  - **Single GPU**: `"T4"`, `"L4"`, `"L40"`, `"A10G"`
  - **Multi GPU**: `"T4_X_4"`, `"L4_X_4"`, `"L4_X_8"`, `"A100_X_8"`, `"H100_X_8"`

**Usage:**
```bash
# Switch from T4 to L4 without stopping
curl -F "auth_file=@auth.json" -F "machine_type=L4" http://localhost:5000/api/v2/switch-machine

# Switch to high-performance H100
curl -F "auth_file=@auth.json" -F "machine_type=H100_X_8" http://localhost:5000/api/v2/switch-machine
```

**Response:**
```json
{
  "success": true,
  "studio_name": "my-studio",
  "message": "Successfully switched from T4 to L4",
  "previous_machine": "T4",
  "new_machine": "L4",
  "switch_duration_seconds": 45.2,
  "timestamp": "2024-01-15T10:30:00"
}
```

**Note:** Studio must be running to switch machine types. This uses Lightning's built-in seamless machine switching.

#### `POST /api/v2/stop`
Stop the studio.

**Parameters:**
- `wait_for_stopped` (optional): `"true"` or `"false"` (default: `"true"`)  
- `timeout` (optional): Timeout in seconds (default: `"300"`)

**Response:**
```json
{
  "success": true,
  "studio_name": "my-studio",
  "message": "Studio stopped",
  "timestamp": "2024-01-15T10:30:00"
}
```

### Machine Types and Pricing

#### `GET|POST /api/v2/machine-types`
Get all available machine types with pricing and specifications.

**Authentication:** Lightning AI credentials only (no studio required)

**Usage Examples:**

```bash
# Using curl (GET method - default)
curl -F "auth_file=@auth.json" http://localhost:5000/api/v2/machine-types

# Using curl (POST method)
curl -X POST -F "auth_file=@auth.json" http://localhost:5000/api/v2/machine-types
```

**Python Example:**
```python
import requests

# Get machine types
response = requests.get('http://localhost:5000/api/v2/machine-types', 
                       files={'auth_file': open('examples/minimal_auth_example.json', 'rb')})

data = response.json()
if data['success']:
    print(f"Found {data['total_machines']} machines:")
    for machine in data['machines']:
        gpu_info = f"{machine['gpu_count']}x {machine['gpu_type']}" if machine['gpu_count'] > 0 else "CPU only"
        print(f"• {machine['name']}: ${machine['cost_per_hour']:.2f}/hr - {gpu_info}")
```

**Response:**
```json
{
  "success": true,
  "total_machines": 19,
  "machines": [
    {
      "name": "T4",
      "lightning_sdk_name": "T4",
      "family": "T4",
      "instance_id": "g4dn.xlarge",
      "cost_per_hour": 0.19,
      "spot_price_per_hour": 0.54252,
      "savings_percentage": -185.54,
      "cpu_cores": 4,
      "memory_gb": 15,
      "gpu_count": 1,
      "gpu_type": "nvidia-tesla-t4",
      "availability_seconds": "52",
      "available_zones": 13,
      "enabled": true,
      "tier_restricted": false,
      "out_of_capacity": false
    },
    {
      "name": "L4",
      "lightning_sdk_name": "L4",
      "family": "L4", 
      "instance_id": "g6.4xlarge",
      "cost_per_hour": 1.58,
      "spot_price_per_hour": 0.93632,
      "savings_percentage": 40.74,
      "cpu_cores": 16,
      "memory_gb": 62,
      "gpu_count": 1,
      "gpu_type": "nvidia-tesla-l4",
      "availability_seconds": "57",
      "available_zones": 4,
      "enabled": true,
      "tier_restricted": false,
      "out_of_capacity": false
    }
  ],
  "sdk_mapping": {
    "T4": [{"instance_id": "g4dn.xlarge", "cost_per_hour": 0.19, "display_name": "T4"}],
    "L4": [{"instance_id": "g6.4xlarge", "cost_per_hour": 1.58, "display_name": "L4"}],
    "CPU": [{"instance_id": "m7i-flex.large", "cost_per_hour": 0.29, "display_name": "Default (CPU)"}]
  },
  "available_sdk_names": ["A100_X_8", "CPU", "DATA_PREP", "H100_X_8", "L4", "L40", "T4", "T4_X_4"],
  "usage_note": "Use 'lightning_sdk_name' values when starting studios with /api/v2/start",
  "timestamp": "2024-01-15T10:30:00"
}
```

**Machine Types Available:**
- **CPU Machines**: Default (CPU), Data prep - Starting from $0.29/hr
- **GPU Machines**: 
  - T4: $0.19/hr (1 GPU) to $4.55/hr (4 GPUs)
  - L4: $1.58/hr (1 GPU) to $15.03/hr (8 GPUs)  
  - L40S: $2.89/hr (1 GPU) to $37.89/hr (8 GPUs)
  - A100: $27.67/hr (8 GPUs) - Tier restricted
  - H100: $64.96/hr (8 GPUs) - Tier restricted
  - H200: $70.53/hr (8 GPUs) - Tier restricted

**Key Fields:**
- `cost_per_hour`: Regular pricing
- `spot_price_per_hour`: Spot instance pricing  
- `savings_percentage`: Savings with spot instances
- `tier_restricted`: Requires higher tier subscription
- `out_of_capacity`: Currently unavailable
- `availability_seconds`: Expected wait time for availability

### Command Execution

#### `POST /api/v2/execute`
Execute a command on the studio.

**Parameters:**
- `command` (required): Command to execute
- `timeout` (optional): Timeout in seconds (default: `"300"`)

**Response:**
```json
{
  "success": true,
  "studio_name": "my-studio", 
  "command": "python script.py",
  "return_code": 0,
  "stdout": "Script output here...",
  "stderr": "",
  "execution_time": 2.5
}
```

### File Operations

#### `POST /api/v2/upload`
Upload a file to the studio.

**Parameters:**
- `file` (required): File to upload (form field)
- `remote_path` (optional): Remote destination path

**Response:**
```json
{
  "success": true,
  "studio_name": "my-studio",
  "message": "File uploaded successfully to script.py",
  "remote_path": "script.py",
  "filename": "script.py"
}
```

#### `GET/POST /api/v2/download/<file_path>`
Download a file from the studio.

**Parameters:**
- `file_path`: Path to file in URL

**Response:** File download or JSON error

#### `GET/POST /api/v2/files`
List files in studio directory.

**Parameters:**
- `path` (optional): Directory path (default: `"."`)

**Response:**
```json
{
  "success": true,
  "studio_name": "my-studio",
  "path": ".",
  "files": [
    {
      "name": "script.py",
      "type": "file", 
      "size": "1024",
      "permissions": "-rw-r--r--"
    }
  ]
}
```

### Utility

#### `GET /api/machine-types`
Get available machine types (no auth required).

**Response:**
```json
{
  "machine_types": [
    {"name": "CPU", "value": "CPU", "description": "CPU-only machine", "category": "cpu"},
    {"name": "T4", "value": "T4", "description": "NVIDIA T4 - Good for inference", "category": "gpu"},
    {"name": "A100", "value": "A100", "description": "NVIDIA A100 - Top performance", "category": "gpu"},
    {"name": "H100", "value": "H100", "description": "NVIDIA H100 - Latest generation", "category": "gpu"}
  ],
  "categories": {
    "cpu": [...],
    "gpu": [...], 
    "multi_gpu": [...]
  },
  "cloud_providers": ["AWS", "GCP", "AZURE"],
  "notes": {
    "variant_independent": "A100 automatically chooses best variant per cloud",
    "max_runtime": "Some machines support max_runtime parameter"
  }
}
```

---

## 💻 Usage Examples

### curl Examples

```bash
# Create full auth file for studio operations
cat > auth.json << EOF
{
  "studio_name": "my-studio",
  "teamspace": "my-team",
  "username": "my-user",
  "lightning_user_id": "your-lightning-user-id",
  "lightning_api_key": "your-lightning-api-key"
}
EOF

# Create minimal auth file for account operations
cat > minimal_auth.json << EOF
{
  "lightning_user_id": "your-lightning-user-id",
  "lightning_api_key": "your-lightning-api-key"
}
EOF

# Check account balance
curl -F "auth_file=@minimal_auth.json" \
  http://localhost:5000/api/v2/balance

# List all studios
curl -F "auth_file=@minimal_auth.json" \
  http://localhost:5000/api/v2/list/studios

# Get studio status
curl -F "auth_file=@auth.json" \
  http://localhost:5000/api/v2/status

# Start studio with GPU
curl -F "auth_file=@auth.json,machine_type=GPU" \
  http://localhost:5000/api/v2/start

# Execute command
curl -F "auth_file=@auth.json,command=python --version" \
  http://localhost:5000/api/v2/execute

# Upload file
curl -F "auth_file=@auth.json" \
     -F "file=@my_script.py" \
     -F "remote_path=scripts/my_script.py" \
     http://localhost:5000/api/v2/upload

# Download file
curl -F "auth_file=@auth.json" \
  http://localhost:5000/api/v2/download/output.txt \
  -o downloaded_output.txt

# List files
curl -F "auth_file=@auth.json,path=scripts" \
  http://localhost:5000/api/v2/files

# Stop studio
curl -F "auth_file=@auth.json" \
  http://localhost:5000/api/v2/stop
```

### Python Examples

```python
import requests
import json

# Method 1: Using file upload
with open('auth.json', 'rb') as f:
    # Get status
    response = requests.post(
        'http://localhost:5000/api/v2/status',
        files={'auth_file': f}
    )
    status = response.json()
    print(f"Status: {status['status']}")

# Method 2: Using JSON body
auth = {
    "studio_name": "my-studio",
    "teamspace": "my-team", 
    "username": "my-user",
    "lightning_user_id": "your-lightning-user-id",
    "lightning_api_key": "your-lightning-api-key"
}

# Start studio
response = requests.post(
    'http://localhost:5000/api/v2/start',
    json={"auth": auth, "machine_type": "GPU"}
)
result = response.json()

# Execute command
response = requests.post(
    'http://localhost:5000/api/v2/execute',
    json={"auth": auth, "command": "python train_model.py"}
)
execution = response.json()
print(f"Output: {execution['stdout']}")

# Upload file
with open('script.py', 'rb') as f:
    response = requests.post(
        'http://localhost:5000/api/v2/upload',
        files={'auth_file': open('auth.json', 'rb'), 'file': f},
        data={'remote_path': 'my_script.py'}
    )
    upload_result = response.json()
```

### JavaScript Examples

```javascript
// Method 1: Using fetch with FormData (file upload)
const authFile = new File([JSON.stringify({
  studio_name: "my-studio",
  teamspace: "my-team",
  username: "my-user", 
  lightning_user_id: "your-lightning-user-id",
  lightning_api_key: "your-lightning-api-key"
})], "auth.json");

const formData = new FormData();
formData.append('auth_file', authFile);

// Get status
const statusResponse = await fetch('http://localhost:5000/api/v2/status', {
  method: 'POST',
  body: formData
});
const status = await statusResponse.json();

// Start studio
const startFormData = new FormData();
startFormData.append('auth_file', authFile);
startFormData.append('machine_type', 'GPU');

const startResponse = await fetch('http://localhost:5000/api/v2/start', {
  method: 'POST', 
  body: startFormData
});

// Method 2: Using JSON body
const auth = {
  studio_name: "my-studio",
  teamspace: "my-team",
  username: "my-user",
  lightning_user_id: "your-lightning-user-id", 
  lightning_api_key: "your-lightning-api-key"
};

// Execute command
const executeResponse = await fetch('http://localhost:5000/api/v2/execute', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    auth: auth,
    command: "python my_script.py"
  })
});
const execution = await executeResponse.json();
console.log('Output:', execution.stdout);
```

---

## 👥 Multi-User Support

Each user maintains their own Lightning AI credentials and studio access:

### User 1 Auth File (`alice_auth.json`)
```json
{
  "studio_name": "alice-dev-studio",
  "teamspace": "team-alpha",
  "username": "alice",
  "lightning_user_id": "alice-lightning-user-id",
  "lightning_api_key": "alice-lightning-api-key"
}
```

### User 2 Auth File (`bob_auth.json`) 
```json
{
  "studio_name": "bob-prod-studio",
  "teamspace": "team-beta", 
  "username": "bob",
  "lightning_user_id": "bob-lightning-user-id",
  "lightning_api_key": "bob-lightning-api-key"
}
```

### Concurrent Usage
```bash
# Alice starts her studio
curl -F "auth_file=@alice_auth.json,machine_type=GPU" \
  http://localhost:5000/api/v2/start

# Bob starts his studio (simultaneously)
curl -F "auth_file=@bob_auth.json,machine_type=CPU" \
  http://localhost:5000/api/v2/start

# Each user operates independently
curl -F "auth_file=@alice_auth.json,command=python alice_model.py" \
  http://localhost:5000/api/v2/execute

curl -F "auth_file=@bob_auth.json,command=python bob_analysis.py" \
  http://localhost:5000/api/v2/execute
```

### Security Features
- ✅ **Credential Isolation**: Each request uses only that user's credentials
- ✅ **No Cross-User Access**: Users cannot access each other's studios
- ✅ **Thread-Safe**: Multiple users can operate simultaneously  
- ✅ **Stateless**: No server-side user data storage
- ✅ **Per-Request Auth**: Credentials are validated for each operation

---

## 🐳 Docker Deployment

### Build and Run
```bash
# Build image
docker build -t lightning-api .

# Run container
docker run -p 5000:5000 lightning-api

# Run with environment variables
docker run -p 5000:5000 \
  -e DEBUG=false \
  -e PORT=5000 \
  lightning-api
```

### Docker Compose
```yaml
version: '3.8'
services:
  lightning-api:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DEBUG=false
      - PORT=5000
    restart: unless-stopped
```

### Production Deployment
```bash
# With load balancer
docker run -d --name lightning-api-1 -p 5001:5000 lightning-api
docker run -d --name lightning-api-2 -p 5002:5000 lightning-api
docker run -d --name lightning-api-3 -p 5003:5000 lightning-api

# Use nginx/traefik to load balance across instances
```

---

## 🔧 Configuration

### Environment Variables
```bash
# Server settings
PORT=5000                    # Server port (default: 5000)
DEBUG=false                  # Debug mode (default: false)
SECRET_KEY=your-secret-key   # Flask secret key

# Optional: Default Lightning AI settings
DEFAULT_STUDIO_NAME=my-studio
DEFAULT_TEAMSPACE=my-team  
DEFAULT_USERNAME=my-user
```

### Error Handling
All endpoints return consistent error format:
```json
{
  "success": false,
  "error": "Error description",
  "timestamp": "2024-01-15T10:30:00"
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad request (missing parameters, invalid data)
- `401`: Unauthorized (invalid credentials)
- `500`: Internal server error

---

## 📞 Support

- **Documentation**: See additional `.md` files in the repository
- **Issues**: Create GitHub issues for bugs/features
- **API Health**: `GET /health` for server status
- **API Info**: `GET /` for endpoint documentation

---

**Lightning-API v2.0** - Making Lightning AI Studio management simple and powerful! ⚡