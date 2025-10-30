#!/usr/bin/env python3
"""
Simple Water Level Monitoring System for Raspberry Pi

This is a simplified version without Philips Hue and Pushover integration.
It monitors the water level using an HC-SR04 ultrasonic sensor and provides
console output with logging capabilities.

Features:
- Distance measurement with HC-SR04 ultrasonic sensor
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
from typing import Optional
from collections import deque
from statistics import median

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('water_level_simple.log')
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

    # Speed of sound in cm/s (at 20°C)
    SPEED_OF_SOUND: float = 34300.0


class SimpleWaterLevelMonitor:
    """Simple water level monitoring system without external integrations."""

    def __init__(self, config: Configuration):
        """Initialize the water level monitor.

        Args:
            config: Configuration object containing system parameters
        """
        self.config = config
        self.running: bool = False
        self.measurement_thread: Optional[threading.Thread] = None
        self.distance_readings: deque = deque(maxlen=config.SENSOR_READINGS_FILTER_SIZE)

        # Initialize GPIO
        self._setup_gpio()

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

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals gracefully.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()

    def get_distance(self) -> Optional[float]:
        """Measure distance using ultrasonic sensor.

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

    def monitor_distance(self) -> None:
        """Main monitoring loop - continuously measures and displays distance."""
        logger.info("Starting distance monitoring")

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

                # Determine status
                if water_level_pct >= self.config.CRITICAL_WATER_LEVEL:
                    status = "CRITICAL"
                elif water_level_pct >= self.config.SAFE_WATER_LEVEL:
                    status = "WARNING"
                else:
                    status = "SAFE"

                # Log current status with color coding info
                logger.info(
                    f"Distance: {distance:.2f} cm | "
                    f"Water Level: {water_level_pct:.2f}% | "
                    f"Status: {status}"
                )

                # Wait before next measurement
                time.sleep(self.config.MEASUREMENT_INTERVAL)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                time.sleep(self.config.MEASUREMENT_INTERVAL)

    def start(self) -> None:
        """Start the distance monitoring system."""
        if self.running:
            logger.warning("Monitor is already running")
            return

        self.running = True
        self.measurement_thread = threading.Thread(
            target=self.monitor_distance,
            daemon=True,
            name="DistanceMonitor"
        )
        self.measurement_thread.start()
        logger.info("Distance monitor started")

    def stop(self) -> None:
        """Stop the distance monitoring system gracefully."""
        if not self.running:
            return

        logger.info("Stopping distance monitor...")
        self.running = False

        # Wait for thread to finish
        if self.measurement_thread and self.measurement_thread.is_alive():
            self.measurement_thread.join(timeout=5.0)

        # Cleanup GPIO
        try:
            GPIO.cleanup()
            logger.info("GPIO cleaned up successfully")
        except Exception as e:
            logger.error(f"Error cleaning up GPIO: {e}")

        logger.info("Distance monitor stopped")

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
    """Main entry point for the simple water level monitoring system.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    logger.info("=" * 60)
    logger.info("Simple Water Level Monitoring System Starting")
    logger.info("=" * 60)

    config = Configuration()

    try:
        # Create and run monitor
        monitor = SimpleWaterLevelMonitor(config)
        monitor.run()
        return 0

    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
