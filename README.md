# Raspberry Pi Water Level Monitor

A professional-grade water level monitoring system for Raspberry Pi that uses an ultrasonic distance sensor to monitor water levels and automatically control a pump via Philips Hue smart socket, with push notifications via Pushover.

## Features

### Core Functionality
- **Automatic Water Level Monitoring**: Continuously measures water level using HC-SR04 ultrasonic sensor
- **Smart Pump Control**: Automatically controls pump via Philips Hue smart socket based on water level thresholds
- **Push Notifications**: Sends alerts via Pushover when water levels reach critical thresholds
- **Sensor Filtering**: Median filter for stable and accurate readings

### Code Quality & Reliability
- **Comprehensive Error Handling**: Robust error handling for GPIO, network, and sensor operations
- **Sensor Timeouts**: Protection against hanging on sensor failures
- **Graceful Shutdown**: Proper cleanup and signal handling (SIGINT, SIGTERM)
- **Logging System**: Detailed logging with both console and file output
- **Type Hints**: Full type annotations for better code reliability
- **Comprehensive Docstrings**: Detailed documentation for all classes and functions

### Configuration
- **Environment Variable Support**: Configure via environment variables for security
- **Notification Debouncing**: Prevents notification spam with configurable cooldown period
- **Configurable Thresholds**: Easily adjust water level thresholds and sensor parameters

## Files

- **Main.py**: Full-featured version with Philips Hue and Pushover integration
- **ohne_bridge.py**: Simplified version without external integrations (for testing or standalone use)

## Prerequisites

### Hardware
- Raspberry Pi (tested on Raspberry Pi 4)
- HC-SR04 Ultrasonic Distance Sensor
- Philips Hue Bridge (for Main.py)
- Philips Hue smart socket or compatible smart plug (for Main.py)
- Jumper wires for connections

### Software
- Raspberry Pi OS (Raspbian)
- Python 3.7+
- Required Python libraries (see Installation)

## Installation

### 1. Hardware Setup

Connect the HC-SR04 sensor to your Raspberry Pi:
- VCC → 5V Power
- GND → Ground
- TRIG → GPIO Pin 7 (Board numbering)
- ECHO → GPIO Pin 11 (Board numbering)

### 2. Install Required Libraries

```bash
# Update system packages
sudo apt-get update

# Install Python dependencies
pip3 install RPi.GPIO phue pushover

# Or use requirements.txt if available
pip3 install -r requirements.txt
```

### 3. Configuration

#### Option A: Environment Variables (Recommended for security)

```bash
# Set environment variables
export HUE_BRIDGE_IP="192.168.0.137"
export PUSHOVER_USER_KEY="your_user_key_here"
export PUSHOVER_API_TOKEN="your_api_token_here"
```

To make these permanent, add them to `~/.bashrc` or create a `.env` file.

#### Option B: Direct Configuration

Edit the Configuration class in the Python files to set:
- `BRIDGE_IP`: Your Philips Hue Bridge IP address
- `PUSHOVER_USER_KEY`: Your Pushover user key
- `PUSHOVER_API_TOKEN`: Your Pushover API token

### 4. Philips Hue Setup

1. Press the link button on your Philips Hue Bridge
2. Run the script within 30 seconds to establish connection
3. Ensure your pump is connected to a Hue-compatible smart socket named "Pumpe"
4. You can change the socket name in the Configuration class (`PUMP_LIGHT_NAME`)

### 5. Pushover Setup

1. Create a Pushover account at https://pushover.net/
2. Create an application to get your API token
3. Note your user key from the dashboard

## Usage

### Running the Full System

```bash
# Make the script executable
chmod +x Main.py

# Run the monitoring system
python3 Main.py

# Or run in background
nohup python3 Main.py > water_monitor.out 2>&1 &
```

### Running the Simple Version (No External Integrations)

```bash
# Make the script executable
chmod +x ohne_bridge.py

# Run the simple monitor
python3 ohne_bridge.py
```

### Running as a System Service (Recommended for Production)

Create a systemd service file `/etc/systemd/system/water-monitor.service`:

```ini
[Unit]
Description=Water Level Monitor
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/RaspberyPI
Environment="HUE_BRIDGE_IP=192.168.0.137"
Environment="PUSHOVER_USER_KEY=your_key"
Environment="PUSHOVER_API_TOKEN=your_token"
ExecStart=/usr/bin/python3 /home/pi/RaspberyPI/Main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable water-monitor.service
sudo systemctl start water-monitor.service

# Check status
sudo systemctl status water-monitor.service

# View logs
sudo journalctl -u water-monitor.service -f
```

## Configuration Options

### Water Level Thresholds

Edit these values in the `Configuration` class:

```python
MAX_WATER_LEVEL = 30.0           # Maximum water level in cm
CRITICAL_WATER_LEVEL = 80.0       # Critical threshold (%)
SAFE_WATER_LEVEL = 50.0          # Safe threshold (%)
```

### Sensor Settings

```python
SENSOR_TIMEOUT = 1.0                    # Sensor timeout in seconds
SENSOR_READINGS_FILTER_SIZE = 5         # Number of readings to filter
MEASUREMENT_INTERVAL = 1.0              # Time between measurements
```

### Notification Settings

```python
NOTIFICATION_COOLDOWN = 300      # Minimum seconds between notifications (5 min)
```

## How It Works

1. **Initialization**: The system initializes GPIO pins, connects to Philips Hue Bridge, and sets up Pushover client
2. **Monitoring Loop**:
   - Continuously measures distance to water surface
   - Applies median filtering for stable readings
   - Calculates water level as percentage of maximum
3. **Automatic Control**:
   - When water level ≥ 80% (critical): Turns pump ON and sends notification
   - When water level < 50% (safe) and pump is ON: Turns pump OFF and sends notification
4. **Graceful Shutdown**: On SIGINT or SIGTERM, safely turns off pump and cleans up GPIO

## Logging

The system creates detailed logs:

- **Console Output**: Real-time status information
- **Log File**:
  - `water_level_monitor.log` (Main.py)
  - `water_level_simple.log` (ohne_bridge.py)

Log levels include:
- INFO: Normal operations and status updates
- WARNING: Non-critical issues (sensor timeouts, invalid readings)
- ERROR: Errors that don't stop the system
- CRITICAL: Fatal errors

## Troubleshooting

### Sensor Not Responding

- Check wiring connections
- Verify GPIO pin numbers match configuration
- Check sensor timeout settings
- Review logs for specific error messages

### Cannot Connect to Philips Hue Bridge

- Verify Bridge IP address is correct
- Ensure Raspberry Pi and Bridge are on same network
- Press the link button on Bridge before running script
- Check Bridge connectivity with: `ping <bridge_ip>`

### Pump Not Responding

- Verify the smart socket name matches `PUMP_LIGHT_NAME` in configuration
- Check that socket is properly connected to Hue Bridge
- Test manual control via Hue app

### Notifications Not Sending

- Verify Pushover credentials are correct
- Check network connectivity
- Review notification cooldown settings
- Check logs for error messages

### Permission Errors

```bash
# Add user to gpio group
sudo usermod -a -G gpio $USER

# Reboot for changes to take effect
sudo reboot
```

## Safety Considerations

- The system automatically turns OFF the pump during shutdown
- Notifications have a cooldown period to prevent spam
- Comprehensive error handling prevents crashes
- Sensor readings are validated and filtered

## Code Improvements from Original Version

✅ **Added comprehensive error handling**
✅ **Fixed potential bugs in distance measurement**
✅ **Implemented timeout protection for sensor**
✅ **Added logging system (replaces print statements)**
✅ **Implemented sensor reading filtering (median filter)**
✅ **Added notification debouncing/cooldown**
✅ **Full type hints and docstrings**
✅ **Graceful shutdown with signal handling**
✅ **Configuration via environment variables**
✅ **Object-oriented architecture**
✅ **Thread-safe operations**
✅ **Validation for sensor readings**

## Contributing

Contributions are welcome! Areas for potential enhancement:

- Additional notification services (Telegram, Discord, etc.)
- Web dashboard for monitoring
- Historical data logging and graphing
- Multiple sensor support
- Temperature compensation for distance calculations
- Configuration file support (YAML/JSON)
- Unit tests

Please create a pull request with your improvements.

## License

This project is licensed under the [MIT License](LICENSE).

## Acknowledgments

- Uses the `phue` library for Philips Hue integration
- Uses the `pushover` library for notifications
- Built with `RPi.GPIO` for Raspberry Pi GPIO control
