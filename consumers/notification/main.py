import json
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    "order-placed",
    bootstrap_servers="kafka:9092",
    group_id="notification-group",
    auto_offset_reset="earliest",
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
)

print("Notification consumer started, listening on order-placed...")

for message in consumer:
    event = message.value
    print(f"[notification] Sending confirmation for order {event['order_id']} "
          f"({event['quantity']} x {event['item']})")
