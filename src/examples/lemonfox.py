#!/usr/bin/env python3
from typing import Final

import requests

SAMPLE: Final = """
The primary goal is to discuss and elaborate on general thoughts around ML and AI strategy. Outline areas in which we can benefit from recent and near future advances in AI/ML. On the contrary, also describe areas which we will benefit from sticking to classical algorithms and software engineering.

The primary goal of this strategy should be to serve the scale-up of our robotics fleet as much as possible and not to create another software product orthogonal to the filics runners.
"""

url = "https://api.lemonfox.ai/v1/audio/speech"
headers = {"Authorization": "Bearer YOUR_API_KEY", "Content-Type": "application/json"}
data = {"input": SAMPLE, "voice": "santa", "response_format": "mp3"}

response = requests.post(url, headers=headers, json=data)
with open("speech.mp3", "wb") as f:
    f.write(response.content)
