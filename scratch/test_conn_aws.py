import boto3
import json
import psycopg2

def test_conn():
    try:
        client = boto3.client("secretsmanager", region_name="ap-south-1")
        response = client.get_secret_value(SecretId="mri-dev-db-credentials")
        secret = json.loads(response["SecretString"])
        print("Got secret!")
        
        conn = psycopg2.connect(
            host=secret["host"],
            port=secret.get("port", 5432),
            dbname=secret["dbname"],
            user=secret["username"],
            password=secret["password"],
            sslmode="require",
            connect_timeout=5
        )
        print("SUCCESS connecting with fetched secret!")
        
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM daily_prices;")
        print(f"daily_prices count: {cur.fetchone()[0]}")
        
    except Exception as e:
        print(f"FAIL: {e}")

if __name__ == '__main__':
    test_conn()
