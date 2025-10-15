"""
Machine types and cloud providers for Lightning AI SDK
Based on official Lightning AI documentation
"""

# Common machine types from Lightning AI SDK documentation
AVAILABLE_MACHINES = [
    # CPU machines
    "CPU",
    
    # GPU machines - commonly available
    "T4",           # NVIDIA T4
    "L4",           # NVIDIA L4
    "A10G",         # NVIDIA A10G
    "A100",         # NVIDIA A100 (variant independent)
    "A100_40GB",    # NVIDIA A100 40GB
    "A100_80GB",    # NVIDIA A100 80GB
    "H100",         # NVIDIA H100
    "H200",         # NVIDIA H200
    
    # Multi-GPU variants
    "A100_X_8",     # 8x A100 (variant independent)
    "A100_40GB_X_8", # 8x A100 40GB
    "A100_80GB_X_8", # 8x A100 80GB
    
    # Legacy/simplified names
    "GPU",          # Generic GPU
    "GPU_FAST",     # Fast GPU
]

# Cloud providers
CLOUD_PROVIDERS = [
    "AWS",
    "GCP", 
    "AZURE"
]

def get_machine_info():
    """Get machine type information"""
    return {
        "cpu_machines": ["CPU"],
        "gpu_machines": [m for m in AVAILABLE_MACHINES if m != "CPU"],
        "multi_gpu": [m for m in AVAILABLE_MACHINES if "_X_" in m],
        "cloud_providers": CLOUD_PROVIDERS,
        "notes": {
            "variant_independent": "A100, A100_X_8 automatically choose best variant per cloud",
            "aws_specific": "A100_40GB variants typically available",
            "gcp_specific": "A100_80GB variants typically available", 
            "max_runtime": "Some machines (especially GCP) support max_runtime parameter"
        }
    }

def validate_machine_type(machine_type_str):
    """Validate if machine type is supported"""
    return machine_type_str in AVAILABLE_MACHINES

def get_machine_suggestions(invalid_machine):
    """Get suggestions for invalid machine types"""
    suggestions = []
    invalid_lower = invalid_machine.lower()
    
    for machine in AVAILABLE_MACHINES:
        if invalid_lower in machine.lower() or machine.lower() in invalid_lower:
            suggestions.append(machine)
    
    return suggestions[:5]  # Top 5 suggestions