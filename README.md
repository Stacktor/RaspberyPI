# Raspberry Pi Water Level Monitor

This project uses a Raspberry Pi to monitor the water level in a tank and control a pump based on the water level. It utilizes an ultrasonic distance sensor, the Philips Hue bridge for controlling a smart light socket, and the Pushover service for sending notifications.

## Prerequisites

- Raspberry Pi with Raspbian OS
- Python 3
- RPi.GPIO library
- phue library
- pushover library

## Installation

1. Connect the ultrasonic distance sensor to the Raspberry Pi GPIO pins.
2. Install the required libraries by running the following commands:

    ```shell
    pip install RPi.GPIO
    pip install phue
    pip install pushover
    ```

3. Update the `bridge_ip`, `pushover_user_key`, and `pushover_api_token` variables in the code with your own values.

## Usage

1. Run the script using the following command:

    ```shell
    python3 water_level_monitor.py
    ```

2. The script will continuously monitor the water level and control the pump accordingly.
3. If the water level exceeds the critical threshold, the pump will be turned on and a notification will be sent.
4. If the water level drops below the safe threshold and the pump is running, it will be turned off.

## Contributing

Contributions are welcome! If you have any suggestions or improvements, please create a pull request.

## License

This project is licensed under the [MIT License](LICENSE).