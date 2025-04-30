import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.utils.constants import POSSIBLE_DIAGNOSES
except ImportError:
    print("Error: Could not import POSSIBLE_DIAGNOSES from src.utils.constants")
    sys.exit(1)

def export_to_json(output_file="medical_data.json"):
    """
    Export the POSSIBLE_DIAGNOSES from constants.js to a JSON file
    
    Args:
        output_file: Path to the output JSON file
    """
    medical_data = {
        "diagnostics": POSSIBLE_DIAGNOSES,
        "research": []  # Empty research array to be filled later
    }
    
    with open(output_file, 'w') as f:
        json.dump(medical_data, f, indent=2)
    
    print(f"Exported medical data to {output_file}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Export medical data from constants.js to JSON")
    parser.add_argument("--output", default="medical_data.json", help="Path to the output JSON file")
    
    args = parser.parse_args()
    
    export_to_json(args.output)
