#!/usr/bin/env python3
"""
Water Level Monitoring System for Raspberry Pi

This program monitors the water level in a container using an HC-SR04 ultrasonic sensor,
controls a pump via Philips Hue smart socket, and sends notifications via Pushover.

Features:
- Automatic pump control based on water level
- Push notifications for critical water levels
- Sensor reading filtering for stability
- Comprehensive error handling and logging
- Graceful shutdown handling
"""

import RPi.GPIO as GPIO
import time
import threading
import logging
import signal
import sys
import os
from typing import Optional, Tuple
from collections import deque
from statistics import median
from phue import Bridge
from pushover import Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('water_level_monitor.log')
    ]
)
logger = logging.getLogger(__name__)


class Configuration:
    """Configuration management for the water level monitoring system."""

    # GPIO Pin Configuration
    TRIG_PIN: int = 7  # GPIO Pin for TRIG of HC-SR04
    ECHO_PIN: int = 11  # GPIO Pin for ECHO of HC-SR04

    # Water Level Configuration (in cm and percentage)
    MAX_WATER_LEVEL: float = 30.0  # Maximum water level in cm
    CRITICAL_WATER_LEVEL: float = 80.0  # Critical water level percentage
    SAFE_WATER_LEVEL: float = 50.0  # Safe water level percentage

    # Sensor Configuration
    SENSOR_TIMEOUT: float = 1.0  # Maximum time to wait for sensor response (seconds)
    SENSOR_READINGS_FILTER_SIZE: int = 5  # Number of readings to filter
    MEASUREMENT_INTERVAL: float = 1.0  # Time between measurements (seconds)

    # Notification Configuration
    NOTIFICATION_COOLDOWN: int = 300  # Minimum seconds between notifications (5 minutes)

    # Philips Hue Configuration
    BRIDGE_IP: str = os.getenv('HUE_BRIDGE_IP', '192.168.0.137')
    PUMP_LIGHT_NAME: str = 'Pumpe'

    # Pushover Configuration
    PUSHOVER_USER_KEY: str = os.getenv('PUSHOVER_USER_KEY', '')
    PUSHOVER_API_TOKEN: str = os.getenv('PUSHOVER_API_TOKEN', '')

    # Speed of sound in cm/s (at 20°C)
    SPEED_OF_SOUND: float = 34300.0

    @classmethod
    def validate(cls) -> bool:
        """Validate configuration parameters."""
        if not cls.PUSHOVER_USER_KEY or not cls.PUSHOVER_API_TOKEN:
            logger.warning("Pushover credentials not configured. Notifications will be disabled.")
            return False
        return True


class WaterLevelMonitor:
    """Main water level monitoring system."""

    def __init__(self, config: Configuration):
        """Initialize the water level monitor.

        Args:
            config: Configuration object containing system parameters
        """
        self.config = config
        self.pump_enabled: bool = False
        self.last_notification_time: float = 0
        self.running: bool = False
        self.measurement_thread: Optional[threading.Thread] = None
        self.distance_readings: deque = deque(maxlen=config.SENSOR_READINGS_FILTER_SIZE)

        # Initialize components
        self._setup_gpio()
        self.bridge: Optional[Bridge] = self._setup_hue_bridge()
        self.pushover_client: Optional[Client] = self._setup_pushover()

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _setup_gpio(self) -> None:
        """Configure GPIO pins for the ultrasonic sensor."""
        try:
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup(self.config.TRIG_PIN, GPIO.OUT)
            GPIO.setup(self.config.ECHO_PIN, GPIO.IN)
            GPIO.output(self.config.TRIG_PIN, GPIO.LOW)
            logger.info("GPIO pins configured successfully")
        except Exception as e:
            logger.error(f"Failed to configure GPIO pins: {e}")
            raise

    def _setup_hue_bridge(self) -> Optional[Bridge]:
        """Connect to the Philips Hue Bridge.

        Returns:
            Bridge object if successful, None otherwise
        """
        try:
            bridge = Bridge(self.config.BRIDGE_IP)
            bridge.connect()
            logger.info(f"Connected to Philips Hue Bridge at {self.config.BRIDGE_IP}")
            return bridge
        except Exception as e:
            logger.error(f"Failed to connect to Philips Hue Bridge: {e}")
            logger.warning("Pump control will be disabled")
            return None

    def _setup_pushover(self) -> Optional[Client]:
        """Initialize Pushover client for notifications.

        Returns:
            Pushover Client if credentials are configured, None otherwise
        """
        if self.config.PUSHOVER_USER_KEY and self.config.PUSHOVER_API_TOKEN:
            try:
                client = Client(
                    self.config.PUSHOVER_USER_KEY,
                    api_token=self.config.PUSHOVER_API_TOKEN
                )
                logger.info("Pushover client initialized successfully")
                return client
            except Exception as e:
                logger.error(f"Failed to initialize Pushover client: {e}")
                return None
        return None

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals gracefully.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()

    def get_distance(self) -> Optional[float]:
        """Measure distance to water surface using ultrasonic sensor.

        Returns:
            Distance in centimeters, or None if measurement failed
        """
        try:
            # Send ultrasonic pulse
            GPIO.output(self.config.TRIG_PIN, GPIO.HIGH)
            time.sleep(0.00001)  # 10 microsecond pulse
            GPIO.output(self.config.TRIG_PIN, GPIO.LOW)

            # Wait for echo to start (with timeout)
            start_time = time.time()
            timeout_time = start_time + self.config.SENSOR_TIMEOUT

            while GPIO.input(self.config.ECHO_PIN) == 0:
                start_time = time.time()
                if start_time > timeout_time:
                    logger.warning("Sensor timeout waiting for echo start")
                    return None

            # Wait for echo to end (with timeout)
            end_time = time.time()
            timeout_time = end_time + self.config.SENSOR_TIMEOUT

            while GPIO.input(self.config.ECHO_PIN) == 1:
                end_time = time.time()
                if end_time > timeout_time:
                    logger.warning("Sensor timeout waiting for echo end")
                    return None

            # Calculate distance
            duration = end_time - start_time
            distance = (duration * self.config.SPEED_OF_SOUND) / 2

            # Validate reading (typical HC-SR04 range: 2-400 cm)
            if 2.0 <= distance <= 400.0:
                return distance
            else:
                logger.warning(f"Invalid distance reading: {distance:.2f} cm")
                return None

        except Exception as e:
            logger.error(f"Error reading distance sensor: {e}")
            return None

    def get_filtered_distance(self) -> Optional[float]:
        """Get a filtered distance reading using median filter.

        Returns:
            Filtered distance in centimeters, or None if not enough readings
        """
        distance = self.get_distance()
        if distance is not None:
            self.distance_readings.append(distance)

        if len(self.distance_readings) >= 3:
            return median(self.distance_readings)
        return None

    def calculate_water_level_percentage(self, distance: float) -> float:
        """Calculate water level as a percentage of maximum.

        Args:
            distance: Distance to water surface in centimeters

        Returns:
            Water level as percentage (0-100+)
        """
        water_level = max(0, self.config.MAX_WATER_LEVEL - distance)
        percentage = (water_level / self.config.MAX_WATER_LEVEL) * 100
        return max(0, percentage)  # Ensure non-negative

    def control_pump(self, turn_on: bool) -> bool:
        """Control the pump via Philips Hue smart socket.

        Args:
            turn_on: True to turn pump on, False to turn off

        Returns:
            True if successful, False otherwise
        """
        if self.bridge is None:
            logger.warning("Cannot control pump: Hue Bridge not connected")
            return False

        try:
            lights = self.bridge.get_light_objects('name')
            if self.config.PUMP_LIGHT_NAME not in lights:
                logger.error(f"Pump light '{self.config.PUMP_LIGHT_NAME}' not found")
                return False

            pump_light = lights[self.config.PUMP_LIGHT_NAME]

            if turn_on and not self.pump_enabled:
                pump_light.on = True
                self.pump_enabled = True
                logger.info("Pump turned ON")
                return True
            elif not turn_on and self.pump_enabled:
                pump_light.on = False
                self.pump_enabled = False
                logger.info("Pump turned OFF")
                return True

            return True  # No change needed

        except Exception as e:
            logger.error(f"Error controlling pump: {e}")
            return False

    def send_notification(self, message: str, priority: int = 0) -> bool:
        """Send notification via Pushover.

        Args:
            message: Notification message
            priority: Priority level (-2 to 2, default 0)

        Returns:
            True if notification sent successfully, False otherwise
        """
        if self.pushover_client is None:
            logger.debug(f"Notification not sent (client not configured): {message}")
            return False

        # Check cooldown period
        current_time = time.time()
        if current_time - self.last_notification_time < self.config.NOTIFICATION_COOLDOWN:
            logger.debug("Notification skipped due to cooldown period")
            return False

        try:
            self.pushover_client.send_message(
                message,
                title="Water Level Alert",
                priority=priority
            )
            self.last_notification_time = current_time
            logger.info(f"Notification sent: {message}")
            return True
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False

    def monitor_water_level(self) -> None:
        """Main monitoring loop - continuously measures and acts on water level."""
        logger.info("Starting water level monitoring")

        # Wait for sensor to settle
        logger.info("Waiting for sensor to settle...")
        time.sleep(2)

        while self.running:
            try:
                # Get filtered distance reading
                distance = self.get_filtered_distance()

                if distance is None:
                    logger.warning("Failed to get valid distance reading")
                    time.sleep(self.config.MEASUREMENT_INTERVAL)
                    continue

                # Calculate water level percentage
                water_level_pct = self.calculate_water_level_percentage(distance)

                # Log current status
                logger.info(f"Distance: {distance:.2f} cm | Water Level: {water_level_pct:.2f}% | Pump: {'ON' if self.pump_enabled else 'OFF'}")

                # Handle critical water level
                if water_level_pct >= self.config.CRITICAL_WATER_LEVEL:
                    if self.control_pump(True):
                        self.send_notification(
                            f"CRITICAL: Water level at {water_level_pct:.1f}%. Pump activated.",
                            priority=1
                        )

                # Handle safe water level
                elif water_level_pct < self.config.SAFE_WATER_LEVEL and self.pump_enabled:
                    if self.control_pump(False):
                        self.send_notification(
                            f"Water level safe at {water_level_pct:.1f}%. Pump deactivated."
                        )

                # Wait before next measurement
                time.sleep(self.config.MEASUREMENT_INTERVAL)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                time.sleep(self.config.MEASUREMENT_INTERVAL)

    def start(self) -> None:
        """Start the water level monitoring system."""
        if self.running:
            logger.warning("Monitor is already running")
            return

        self.running = True
        self.measurement_thread = threading.Thread(
            target=self.monitor_water_level,
            daemon=True,
            name="WaterLevelMonitor"
        )
        self.measurement_thread.start()
        logger.info("Water level monitor started")

    def stop(self) -> None:
        """Stop the water level monitoring system gracefully."""
        if not self.running:
            return

        logger.info("Stopping water level monitor...")
        self.running = False

        # Turn off pump for safety
        if self.pump_enabled:
            self.control_pump(False)

        # Wait for thread to finish
        if self.measurement_thread and self.measurement_thread.is_alive():
            self.measurement_thread.join(timeout=5.0)

        # Cleanup GPIO
        try:
            GPIO.cleanup()
            logger.info("GPIO cleaned up successfully")
        except Exception as e:
            logger.error(f"Error cleaning up GPIO: {e}")

        logger.info("Water level monitor stopped")

    def run(self) -> None:
        """Run the monitor and wait indefinitely."""
        self.start()

        try:
            # Keep main thread alive
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self.stop()


def main() -> int:
    """Main entry point for the water level monitoring system.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    logger.info("=" * 60)
    logger.info("Water Level Monitoring System Starting")
    logger.info("=" * 60)

    # Validate configuration
    config = Configuration()
    config.validate()

    try:
        # Create and run monitor
        monitor = WaterLevelMonitor(config)
        monitor.run()
        return 0

    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
