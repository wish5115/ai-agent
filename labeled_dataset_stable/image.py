import os
import base64
import requests

API_URL = "https://router.huggingface.co/fal-ai/fal-ai/qwen-image-edit-2511/lora?_subdomain=queue"
headers = {
    "Authorization": f"Bearer {os.environ.get('HF_TOKEN')}",
}

def query(payload):
    with open(payload["inputs"], "rb") as f:
        img = f.read()
        payload["inputs"] = base64.b64encode(img).decode("utf-8")
    response = requests.post(API_URL, headers=headers, json=payload)
    
    # 调试代码
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
    print(f"Response size: {len(response.content)} bytes")
    print(f"Response (first 500 chars): {response.content[:500]}")
    
    return response.content

image_bytes = query({
    "inputs": "/Users/wish/Downloads/FELV-cat.jpg",
    "parameters": {
        "prompt": "Turn the cat into a tiger."
    }
})

# You can access the image with PIL.Image for example
import io
from PIL import Image
image = Image.open(io.BytesIO(image_bytes))