import json
import time
from kafka import KafkaConsumer
import redis
from db import ensure_inventory_table, inventory_table, dynamodb
consumer = KafkaConsumer(
    "order-placed",
    bootstrap_servers="kafka:9092",
    group_id="inventory-group",
    auto_offset_reset="earliest",
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
)
ensure_inventory_table()
redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)
print("Inventory consumer started, listening on order-placed...")
for message in consumer:
    time.sleep(2)
    event = message.value
    product_id = event["item"]
    quantity = event["quantity"]
    print(f"[inventory] Reducing stock for order {event['order_id']}: "
          f"{quantity} x {product_id}")
    try:
        inventory_table.update_item(
            Key={"product_id": product_id},
            UpdateExpression="SET stock_count = stock_count - :qty",
            ConditionExpression="stock_count >= :qty",
            ExpressionAttributeValues={":qty": quantity},
        )
        redis_client.zincrby("hot_products", quantity, product_id)
        print(f"[inventory] {product_id}: stock updated, hot_products updated")
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        print(f"[inventory] {product_id}: insufficient stock for quantity {quantity}")
