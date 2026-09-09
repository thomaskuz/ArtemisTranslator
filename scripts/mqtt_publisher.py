#!/usr/bin/env python3
"""
MQTT Publisher - Sends messages to Artemis MQTT broker
Tests MQTT to MQTT messaging through Artemis
"""

import paho.mqtt.client as mqtt
import json
import time
import sys

class MQTTPublisher:
    def __init__(self, broker, port, topic):
        self.broker = broker
        self.port = port
        self.topic = topic
        self.client = mqtt.Client(client_id="artemis-mqtt-publisher", protocol=mqtt.MQTTv5)
        self.client.username_pw_set("admin", "admin")
        self.message_count = 0
        self.last_publish_time = 0
        self.is_connected = False

    def on_connect(self, client, userdata, connect_flags, reason_code, properties):
        if reason_code == 0:
            self.is_connected = True
            print(f"[✓] Connected to Artemis MQTT ({self.broker}:{self.port})")
            print(f"[!] Publishing to topic: {self.topic}")
            print(f"[!] Sending messages every 5 seconds (Ctrl+C to stop)\n")
        else:
            print(f"[✗] Connection failed with code {reason_code}", file=sys.stderr)
            sys.exit(1)

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print(f"[!] Unexpected disconnection: {rc}")
            self.is_connected = False

    def on_publish(self, client, userdata, mid):
        """Called when message is published"""
        pass

    def on_error(self, client, userdata, error):
        print(f"[✗] MQTT Error: {error}", file=sys.stderr)

    def publish_message(self):
        """Publish a test message"""
        self.message_count += 1

        # Create message payload
        payload = {
            "color": "Red",
            "message_number": self.message_count,
            "timestamp": time.time()
        }

        # Convert to JSON
        message_json = json.dumps(payload)

        # Publish to MQTT broker
        result = self.client.publish(
            topic=self.topic,
            payload=message_json,
            qos=1,  # At least once delivery
            retain=False
        )

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"[✓] Published message #{self.message_count}")
            print(f"    Topic: {self.topic}")
            print(f"    Payload: {message_json}\n")
        else:
            print(f"[✗] Failed to publish message #{self.message_count}", file=sys.stderr)

        self.last_publish_time = time.time()

    def start(self):
        """Start the publisher"""
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_publish = self.on_publish
        self.client.on_error = self.on_error  # type: ignore

        try:
            print(f"[...] Starting MQTT Publisher")
            print(f"[...] Will publish to: {self.topic}")
            print(f"[...] Connecting to {self.broker}:{self.port}...\n")

            # Connect to broker
            self.client.connect(self.broker, self.port, 60)

            # Start the network loop in a background thread
            self.client.loop_start()

            # Wait for connection
            timeout = 10
            start_time = time.time()
            while not self.is_connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)

            if not self.is_connected:
                print(f"[✗] Failed to connect within {timeout} seconds", file=sys.stderr)
                sys.exit(1)

            # Publish messages every 5 seconds
            while True:
                if time.time() - self.last_publish_time >= 5:
                    self.publish_message()
                time.sleep(0.5)

        except KeyboardInterrupt:
            print(f"\n[!] Stopped by user")
            print(f"[!] Total messages published: {self.message_count}")
        except Exception as e:
            print(f"[✗] Error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            self.client.loop_stop()
            self.client.disconnect()

def main():
    # Configuration
    broker = "localhost"
    port = 1883
    topic = "mqtt-queue"  # Publish to same topic as bridge

    print(f"[...] Starting MQTT Publisher\n")

    publisher = MQTTPublisher(broker, port, topic)
    publisher.start()

if __name__ == "__main__":
    main()
