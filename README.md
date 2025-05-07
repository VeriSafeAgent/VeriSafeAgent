![image](https://github.com/user-attachments/assets/d0399cd1-6595-4d72-b75c-91c51f30bf0b)# VeriSafe Agent System

This repository contains the implementation of the VeriSafe Agent System, a framework for safe and verified mobile task automation using AI agents.

## VeriSafeAgent Library

[VeriSafeAgent Library on GitHub](https://github.com/VeriSafeAgent/VeriSafeAgent_Library)

## Installation

Make sure you have:

1. `Python 3.12` 

Then clone this repo and install the required dependencies:

```shell
git clone https://github.com/VeriSafeAgent/VeriSafeAgent.git
cd VeriSafeAgent
pip install --upgrade pip
pip install -r requirements.txt
```

## Configuration

You need to set up your OpenAI API key to use the system. You can do this in one of two ways:

1. Set it as an environment variable:
```shell
export OPENAI_API_KEY="your-api-key-here"
```

2. Or modify the `simulator.py` file to include your API key:
```python
os.environ["OPENAI_API_KEY"] = "your-api-key-here"
```

### Server Configuration

**Important**: When developing an app using the VeriSafe Agent library, ensure that the server address in your app matches the server address used by the VeriSafe Agent System. Both the app and the server must use the same address for proper communication.

## Emulator Setup

Before running the VeriSafe Agent System, you need to set up and run an Android emulator:

1. **Install Android Studio**:
   - Download and install Android Studio from [official website](https://developer.android.com/studio)
   - Make sure to install the Android SDK during the setup process

2. **Create an Android Virtual Device (AVD)**:
   - Open Android Studio
   - Go to Tools > Device Manager
   - Click "Create Virtual Device"
   - Select a device definition (e.g., Pixel 6)
   - Choose a system image (recommend: API 33 or higher)
   - Complete the AVD creation

3. **Start the Android Emulator**:
   ```shell
   # List available emulators
   emulator -list-avds
   
   # Start the emulator (replace [avd_name] with your emulator name)
   emulator -avd [avd_name]
   ```
   Or start directly from Android Studio's Device Manager

4. **Verify Emulator Connection**:
   ```shell
   # Check if emulator is connected
   adb devices
   
   # Should show something like:
   # emulator-5554   device
   ```

### Required Apps

Make sure to install the target apps on your emulator. For example:
- Google Clock (`com.google.android.deskclock`)
- Google Maps (`com.google.android.apps.maps`)
- Other apps you want to test with

You can install apps through:
- Google Play Store on the emulator
- Using adb command:
  ```shell
  adb install path/to/your/app.apk
  ```

## How to Use

The VeriSafe Agent System consists of a simulator and an emulator program that work together to automate mobile tasks. Here's how to use it:

### Basic Usage

1. **Start the Simulator**:
   ```shell
   python simulator.py --mobile_device emulator --agent m3a --verifier vsa --app com.google.android.deskclock --instruction "make alarm am 3:00 and set the timer to 30sec." --save_path ./history/clock
   ```

2. **Start the Emulator Program** (in a new terminal window):
   ```shell
   python mobile_app/emulator.py --agent m3a
   ```

The simulator will automatically connect with the emulator program and begin executing the instructions on the Android emulator.

### Parameters

- `--mobile_device`: Choose between `emulator` or `real` device
- `--agent`: Currently supports `m3a` (Mobile GUI Agent)
- `--verifier`: Currently supports `vsa` (VeriSafe Agent)
- `--app_name`: The package name of the Android app to interact with
- `--instruction`: The natural language instruction for the agent to execute
- `--save_path`: Path to save execution history and logs

### Example Instructions

Here are some example instructions you can try:

1. Simple alarm creation:
```shell
python simulator.py --mobile_device emulator --agent m3a --verifier vsa --app com.google.android.deskclock --instruction "make alarm am 3:00 and set the timer to 30sec." --save_path ./history/clock
```

2. Complex alarm setup:
```shell
python simulator.py --mobile_device emulator --agent m3a --verifier vsa --app com.google.android.deskclock --instruction "Open the Clock app and create three new alarms with the following conditions: The first alarm should be set for 6:30 AM on weekdays (Monday to Friday) and labeled 'Morning Workout'. The second alarm should be set for 8:00 AM on weekends (Saturday and Sunday) and labeled 'Relaxed Morning'. The third alarm should be set for 10:00 PM every night and labeled 'Wind Down' with a vibration-only mode. Once all alarms are created, go to the alarm list, and turn them all on." --save_path ./history/clock
```

## Dataset

The VeriSafe Agent System includes a comprehensive dataset for llamatouch and challenge. The dataset is organized in Dataset.xlsx with the following structure:

### Dataset Structure

The dataset contains information about various mobile applications and their associated instructions:

```
Dataset.xlsx
│
├── APP_NAME                    # Name of the mobile application
├── PACKAGE_NAME               # Name of the mobile application's package
├── INSTRUCTION_NUMBER                      # Number of instructions for each app
├── DATASET_TYPE               # Type of dataset (e.g., llamatouch, challenge)
├── INSTRUCTION_1                # Correct Natural language instructions for the app
└── INSTRUCTION_2                # Wrong Natural language instructions for the app
```

### Predicates

Predicates are essential components of the verification system that define the state of the application and the conditions that must be met for actions to be considered safe. Each application has its own set of predicates defined in JSON format:

```
dataset/predicates/
│
├── GoogleMaps.json
├── GoogleMapsComplex.json
└── [Other App Predicates].json
```

Each predicate has the following components:

- **Description**: A natural language description of what the predicate represents
- **Variables**: The variables that make up the predicate, with their types and possible values

Example predicate from GoogleMaps.json:
```json
{
  "ShakeToSendFeedback": {
    "description": "Indicates whether the 'Shake to send feedback' feature is enabled or disabled in the Google Maps settings.",
    "variables": [
      {
        "name": "shake_to_send_feedback_enabled",
        "type": "Boolean"
      }
    ]
  },
  "NotificationSetting": {
    "description": "Indicates the current status of the 'Notifications' setting in the Google Maps settings.",
    "variables": [
      {
        "name": "notifications_status",
        "type": "Enum",
        "enum_values": ["On", "Off"]
      }
    ]
  },
  "SettingOptions": {
    "description": "Options available in the Google Maps settings.",
    "variables": [
      {
        "name": "setting_option",
        "type": "Enum",
        "enum_values": [
          "Offline Maps Settings",
          "Edit Home or Work",
          "Navigation Settings",
          "Notifications",
          "Distance Units"
        ]
      }
    ]
  }
}
```

## Project Structure

```
VeriSafe_Agent_System_opensource/
│
├── simulator.py                 # Main entry point
├── mobile_gui_agent/            # Mobile GUI agent implementation
│   ├── agent.py                 # Base agent class
│   ├── parser.py                # XML parser for UI elements
│   └── m3a/                     # M3A agent implementation
│       ├── m3a_agent.py         # M3A agent class
│       ├── m3a_prompt.py        # Prompts for the M3A agent
│       └── m3a_parser.py        # Parser for M3A agent
│
├── verisafe_agent_core/         # VeriSafe agent implementation
│   ├── verification_server.py   # Verification server
│   ├── verisafe_agent.py       # VeriSafe agent class
│   ├── verisafe_memory.py      # Memory management for VeriSafe agent
│   └── verisafe_agent_engine/  # Engine components
│
├── env/                         # Environment components
├── utils_/                      # Utility functions
├── model/                       # Model implementations
└── dataset/                     # Dataset for training and evaluation
```

