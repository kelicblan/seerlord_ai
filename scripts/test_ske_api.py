from fastapi.testclient import TestClient
from server.main import app
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

client = TestClient(app)
client.headers["X-API-Key"] = "sk-admin-test"

def test_graph_endpoint():
    print("Testing GET /api/v1/ske/graph...")
    print(f"Client Headers: {client.headers}")
    try:
        response = client.get("/api/v1/ske/graph?limit=10")
        if response.status_code == 200:
            data = response.json()
            print(f"Success! Retrieved {len(data['nodes'])} nodes and {len(data['links'])} links.")
            if len(data['nodes']) > 0:
                print(f"Sample Node: {data['nodes'][0]['name']} ({data['nodes'][0]['labels']})")
        else:
            print(f"Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Exception during graph test: {e}")

if __name__ == "__main__":
    test_graph_endpoint()
