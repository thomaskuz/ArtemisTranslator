#!/usr/bin/env python3
"""
MQTT Subscriber - Listen to Artemis MQTT bridge
Tests AMQP to MQTT bridging in Artemis
"""

import paho.mqtt.client as mqtt
import json
import sys

class MQTTSubscriber:
    def __init__(self, broker, port, topic):
        self.broker = broker
        self.port = port
        self.topic = topic
        self.client = mqtt.Client(client_id="artemis-mqtt-subscriber", protocol=mqtt.MQTTv5)
        self.client.username_pw_set("admin", "admin")
        self.message_count = 0

    def on_connect(self, client, userdata, connect_flags, reason_code, properties):
        if reason_code == 0:
            print(f"[✓] Connected to Artemis MQTT ({self.broker}:{self.port})")
            client.subscribe(self.topic)
            print(f"[!] Subscribed to topic: {self.topic}")
            print(f"[!] Waiting for messages (Ctrl+C to stop)\n")
        else:
            print(f"[✗] Connection failed with code {reason_code}", file=sys.stderr)
            sys.exit(1)

    def on_message(self, client, userdata, msg):
        self.message_count += 1
        print(f"\n{'='*70}")
        print(f"[✓] Message #{self.message_count} received on MQTT")
        print(f"{'='*70}")
        print(f"Topic: {msg.topic}")
        print(f"QoS: {msg.qos}")

        # Display MQTT properties if available
        print(f"\nProperties (MQTT Metadata):")
        if hasattr(msg, 'properties') and msg.properties:
            props = msg.properties
            # MQTT v5 UserProperty is a list of tuples
            if hasattr(props, 'UserProperty') and props.UserProperty:
                for key, value in props.UserProperty:
                    print(f"  {key}: {value}")
            elif hasattr(props, 'user_properties') and props.user_properties:
                for key, value in props.user_properties:
                    print(f"  {key}: {value}")
            else:
                print(f"  None")
        else:
            print(f"  None")

        # Try to parse payload as JSON
        try:
            payload = json.loads(msg.payload.decode())
            print(f"\nPayload (JSON):")
            print(json.dumps(payload, indent=2))
        except (json.JSONDecodeError, UnicodeDecodeError):
            print(f"\nPayload (Raw):")
            print(msg.payload.decode())

        print(f"{'='*70}\n")

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print(f"[!] Unexpected disconnection: {rc}")

    def handle_error(self, client, userdata, error):
        print(f"[✗] MQTT Error: {error}", file=sys.stderr)

    def start(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.on_error = self.handle_error  # type: ignore

        try:
            print(f"[...] Connecting to Artemis MQTT at {self.broker}:{self.port}...")
            print(f"[...] Client ID: {self.client._client_id}")
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_forever()
        except KeyboardInterrupt:
            print(f"\n[!] Stopped by user")
            print(f"[!] Total messages received: {self.message_count}")
        except Exception as e:
            print(f"[✗] Error: {e}", file=sys.stderr)
            sys.exit(1)

def main():
    # Configuration
    broker = "localhost"
    port = 1883  # Artemis MQTT port
    topic = "AMQP/MQTT/FAB/TEST"  # Subscribe to bridge multicast address

    print(f"[...] Starting MQTT Subscriber")
    print(f"[...] Will subscribe to: {topic}")
    print(f"[...] This tests AMQP → MQTT bridging in Artemis\n")

    subscriber = MQTTSubscriber(broker, port, topic)
    subscriber.start()

if __name__ == "__main__":
    main()
