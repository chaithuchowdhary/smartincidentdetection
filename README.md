# Incident Detection

This project uses the Seeed Studio XIAO ESP32S3 Sense board equipped with an OV5640 camera to simulate a real-time, low-power CCTV surveillance system. It leverages a lightweight FOMO (Faster Objects, More Objects) model trained using Edge Impulse to detect critical incidents such as fire accidents, smoke, car collisions, and armed robbery.

This project is designed to detect and manage incidents efficiently.

## 🔧 Hardware Used

- 🧠 [Seeed Studio XIAO ESP32S3 Sense](https://wiki.seeedstudio.com/XIAO_ESP32S3_Sense/)
- 📸 OV5640 Camera (connected onboard)
- 💾 Optional: Micro SD card module for storing footage

## 🧠 Machine Learning Model deployed on the MCU

### Model is trained on:
- Fire accident images 
- Smoke detection images 
- Car collision images 
- Robbery or gun detection images 

Model is exported as a C++ library and deployed directly on the microcontroller.

## 📡 How it Works

1. The onboard OV5640 camera captures live footage.
2. Every frame is passed to the Edge Impulse FOMO model.
3. If a critical event is detected (e.g., fire, gun, smoke, crash):
   - The device sends the image and location (optional) to a remote server via an API endpoint.
   - A trigger is sent only when detection occurs, reducing false alerts and saving bandwidth.


## 🌐 API Interface

The device integrates with a REST API to:
- Upload captured image on detection
- Push alerts (e.g., via Pushbullet, Twilio, or custom dashboard)

## 🚀 Features

- Real-time, on-device incident detection
- Edge ML optimized for ultra-low-power embedded hardware
- Live image streaming and condition-based image capture
- API connectivity for remote alerting

  
## Prerequisites

Ensure you have the following installed:
- [Python 3.x](https://www.python.org/downloads/)
- Required Python libraries (see `requirements.txt`)

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/chaithuchowdhary/smartincidentdetection.git
    cd smartincidentdetection
    ```

2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1. Run the application:
    ```bash
    python app.py
    ```

2. Follow the on-screen instructions to detect and manage incidents.
