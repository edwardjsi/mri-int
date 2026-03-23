import boto3
import sys

def check_active_resources(region_name='ap-south-1'):
    print(f"Checking for prominent active services in region: {region_name}...\n")
    
    # 1. EC2 Instances
    print("--- EC2 Instances ---")
    try:
        ec2 = boto3.client('ec2', region_name=region_name)
        instances = ec2.describe_instances()
        found_ec2 = False
        for reservation in instances.get('Reservations', []):
            for instance in reservation.get('Instances', []):
                state = instance['State']['Name']
                if state != 'terminated':
                    found_ec2 = True
                    name = next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), 'Unnamed')
                    print(f"  - Instance ID: {instance['InstanceId']} | Name: {name} | State: {state} | Type: {instance['InstanceType']}")
        if not found_ec2:
            print("  No active EC2 instances found.")
    except Exception as e:
        print(f"  Error checking EC2: {e}")

    # 2. RDS Databases
    print("\n--- RDS Databases ---")
    try:
        rds = boto3.client('rds', region_name=region_name)
        db_instances = rds.describe_db_instances()
        instances_list = db_instances.get('DBInstances', [])
        if not instances_list:
            print("  No RDS databases found.")
        for db in instances_list:
            print(f"  - DB Identifier: {db['DBInstanceIdentifier']} | Status: {db['DBInstanceStatus']} | Class: {db['DBInstanceClass']}")
    except Exception as e:
        print(f"  Error checking RDS: {e}")

    # 3. ECS Clusters
    print("\n--- ECS Clusters ---")
    try:
        ecs = boto3.client('ecs', region_name=region_name)
        clusters = ecs.list_clusters()
        cluster_arns = clusters.get('clusterArns', [])
        if not cluster_arns:
            print("  No ECS clusters found.")
        else:
            for arn in cluster_arns:
                cluster_info = ecs.describe_clusters(clusters=[arn])['clusters'][0]
                print(f"  - Cluster Name: {cluster_info['clusterName']} | Status: {cluster_info['status']} | Active Services: {cluster_info['activeServicesCount']} | Running Tasks: {cluster_info['runningTasksCount']}")
    except Exception as e:
        print(f"  Error checking ECS: {e}")

    # 4. S3 Buckets (Global, but listed here)
    print("\n--- S3 Buckets ---")
    try:
        s3 = boto3.client('s3')
        buckets = s3.list_buckets()
        bucket_list = buckets.get('Buckets', [])
        if not bucket_list:
            print("  No S3 buckets found.")
        for b in bucket_list:
            print(f"  - Bucket Name: {b['Name']}")
    except Exception as e:
        print(f"  Error checking S3: {e}")


if __name__ == '__main__':
    # You can change the region if your resources might be deployed elsewhere
    check_active_resources(region_name='ap-south-1')
