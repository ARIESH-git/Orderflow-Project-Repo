import boto3

dynamodb = boto3.resource(
    "dynamodb",
    endpoint_url="http://dynamodb-local:8000",
    region_name="us-east-1",
    aws_access_key_id="local",
    aws_secret_access_key="local",
)

INVENTORY_TABLE = "Inventory"

SEED_STOCK = {
    "widget": 100,
}


def ensure_inventory_table():
    existing = dynamodb.meta.client.list_tables()["TableNames"]
    if INVENTORY_TABLE not in existing:
        table = dynamodb.create_table(
            TableName=INVENTORY_TABLE,
            KeySchema=[{"AttributeName": "product_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "product_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()

    table = dynamodb.Table(INVENTORY_TABLE)
    for product_id, stock in SEED_STOCK.items():
        try:
            table.put_item(
                Item={"product_id": product_id, "stock_count": stock},
                ConditionExpression="attribute_not_exists(product_id)",
            )
        except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            pass


inventory_table = dynamodb.Table(INVENTORY_TABLE)
