import os
import boto3
import logging
from datetime import datetime, timedelta, timezone

# Initialize logger and EC2 client
logger = logging.getLogger()
logger.setLevel(logging.INFO)
ec2 = boto3.client('ec2')

def lambda_handler(event, context):
    # Fetch Volume ID from environment variables
    volume_id = os.environ.get('VOLUME_ID')
    if not volume_id:
        logger.error("Environment variable 'VOLUME_ID' is missing.")
        return
        
    retention_days = 30
    tag_key = "CreatedBy"
    tag_value = "Lambda-Backup"
    
    # -------------------------------------------------------------------------
    # STEP 1: Create a snapshot of the specified volume
    # -------------------------------------------------------------------------
    now = datetime.now(timezone.utc)
    description = f"Automated snapshot for {volume_id} taken at {now.strftime('%Y-%m-%d %H:%M:%S')}"
    
    try:
        snapshot = ec2.create_snapshot(
            VolumeId=volume_id,
            Description=description,
            TagSpecifications=[
                {
                    'ResourceType': 'snapshot',
                    'Tags': [
                        {'Key': tag_key, 'Value': tag_value},
                        {'Key': 'Name', 'Value': f"Backup-{volume_id}"}
                    ]
                }
            ]
        )
        created_snapshot_id = snapshot['SnapshotId']
        logger.info(f"CREATED SNAPSHOT ID: {created_snapshot_id} for volume {volume_id}")
    except Exception as e:
        logger.error(f"Failed to create snapshot: {str(e)}")
        raise e

    # -------------------------------------------------------------------------
    # STEP 2: List and delete snapshots older than 30 days
    # -------------------------------------------------------------------------
    cutoff_date = now - timedelta(days=retention_days)
    deleted_snapshots = []
    
    try:
        # Filter snapshots owned by 'self' containing our tracking tag
        paginator = ec2.get_paginator('describe_snapshots')
        page_iterator = paginator.paginate(
            OwnerIds=['self'],
            Filters=[
                {
                    'Name': f'tag:{tag_key}',
                    'Values': [tag_value]
                },
                {
                    'Name': 'volume-id',
                    'Values': [volume_id]
                }
            ]
        )
        
        for page in page_iterator:
            for snap in page['Snapshots']:
                snap_id = snap['SnapshotId']
                snap_start_time = snap['StartTime'] # Already timezone-aware (UTC)
                
                # Check if the snapshot is older than the retention cutoff
                if snap_start_time < cutoff_date:
                    logger.info(f"Deleting older snapshot: {snap_id} (Created: {snap_start_time})")
                    ec2.delete_snapshot(SnapshotId=snap_id)
                    deleted_snapshots.append(snap_id)
                    
        logger.info(f"DELETED SNAPSHOT IDS: {deleted_snapshots}")
        
    except Exception as e:
        logger.error(f"Error during cleanup execution: {str(e)}")
        raise e
        
    return {
        'statusCode': 200,
        'created': created_snapshot_id,
        'deleted': deleted_snapshots
    }
