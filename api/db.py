import boto3

dynamodb = boto3.resource(
    "dynamodb",
    endpoint_url="http://dynamodb-local:8000",
    region_name="us-east-1",
    aws_access_key_id="local",
    aws_secret_access_key="local",
)

ORDERS_TABLE = "Orders"
USERS_TABLE = "Users"


def ensure_orders_table():
    existing = dynamodb.meta.client.list_tables()["TableNames"]
    if ORDERS_TABLE in existing:
        return
    table = dynamodb.create_table(
        TableName=ORDERS_TABLE,
        KeySchema=[{"AttributeName": "order_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "order_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    table.wait_until_exists()


def ensure_users_table():
    existing = dynamodb.meta.client.list_tables()["TableNames"]
    if USERS_TABLE in existing:
        return
    table = dynamodb.create_table(
        TableName=USERS_TABLE,
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    table.wait_until_exists()


orders_table = dynamodb.Table(ORDERS_TABLE)
users_table = dynamodb.Table(USERS_TABLE)
