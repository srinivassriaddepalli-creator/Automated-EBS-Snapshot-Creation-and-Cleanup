I have bundled the complete step-by-step instructions into a clean, downloadable markdown (.md) document.
Click the link below to download the file directly to your machine. You can open it in any Markdown viewer, text editor (like VS Code, Obsidian, or Notepad), or upload it directly into your GitHub repository documentation folder:
📁 Download EBS_Backup_Automation_Documentation.md

## Document Preview & Raw Text
If you need to copy and paste the raw content immediately without downloading the file, here is the exact text contained inside the markdown file:

# Project Documentation: Automated EBS Snapshot Creation and Cleanup

## 📌 Objective:
Automate the process of backing up a target Amazon Elastic Block Store (EBS) volume and purging obsolete backups. This solution utilizes an AWS Lambda function triggered weekly by an Amazon EventBridge schedule to create snapshots, tag them for tracking, and safely remove backups older than a 30-day retention period.


## 🛠️ Step 1: Locate Target EBS Volume DetailsBefore configuring automation, identify the structural block device that requires scheduled backups.

1. Navigate to the **Amazon EC2 Console**.2. On the left-hand navigation sidebar, scroll down to the **Elastic Block Store** section and click on **Volumes**.3. Locate your target volume in the table.
2.  Hover over the **Volume ID** column (e.g., `vol-0a1b2c3d4e5f6g7h8`) and click the double-square **Copy** icon. Save this ID for later use.


<img width="845" height="392" alt="image" src="https://github.com/user-attachments/assets/ae981752-6448-4572-a4bd-72e43e98b5ce" />



## 🔐 Step 2: Configure Lambda IAM Role and PoliciesTo allow the Lambda function to interact with your EC2 infrastructure, create an execution role with precise, principle-of-least-privilege permissions.

### 1. Create the Base Execution Role
1. Navigate to the **IAM Console** ➔ **Roles** ➔ **Create role**.
2. Select **AWS service** as the trusted entity type.3. Select **Lambda** from the Service dropdown menu and click **Next**.
4. In the permissions policy search bar, find and check **`AWSLambdaBasicExecutionRole`** (this allows Lambda to stream logs to Amazon CloudWatch). Click **Next**.
5. Name the role `AWSLambdaExecutionRole` and click **Create role**.

### 2. Attach Custom Inline Backup Policies
1. Open your newly created `AWSLambdaExecutionRole` in the IAM console.
2. Click the **Add permissions** dropdown menu on the right and select **Create inline policy**.
3. Toggle the editor view from Visual to **JSON** and paste the following policy:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:CreateSnapshot",
                "ec2:DescribeSnapshots",
                "ec2:DeleteSnapshot",
                "ec2:CreateTags"
            ],
            "Resource": "*"
        }
    ]
}
```
<img width="958" height="385" alt="image" src="https://github.com/user-attachments/assets/ae1c68ac-a7be-45e6-a7b5-92ebeac88a76" />

4. Click **Next**, name the policy `Lambda-EBS-Snapshot-Permissions`, and click **Create policy**.

<img width="915" height="365" alt="image" src="https://github.com/user-attachments/assets/c18493b5-8c07-445d-9b76-d585cf113531" />

## 💻 Step 3: Deploy the AWS Lambda FunctionDeploy the core processing script inside the Lambda environment.

1. Navigate to the **AWS Lambda Console** ➔ **Create function**.
2. Select **Author from scratch**. Configure the following parameters:
   * **Function name**: `EBS-Weekly-Backup-Cleanup`
   * **Runtime**: `Python 3.12`
3. Expand **Additional settings** at the bottom of the page. Select **Use an existing role** and choose `AWSLambdaExecutionRole` from your list.
4. Click **Create function**.

<img width="954" height="392" alt="image" src="https://github.com/user-attachments/assets/d4effa1b-c13e-4422-966b-f09849f02802" />

5. In the **Code** tab editor view, open `lambda_function.py`, erase the boilerplate text completely, and paste the production code below:
```python
import os
import boto3
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ec2 = boto3.client('ec2')

def lambda_handler(event, context):
    volume_id = os.environ.get('VOLUME_ID')
    if not volume_id:
        logger.error("Environment variable 'VOLUME_ID' is missing.")
        return {"statusCode": 400, "body": "Missing VOLUME_ID variable"}
        
    retention_days = 30
    tag_key = "CreatedBy"
    tag_value = "Lambda-Backup"
    
    now = datetime.now(timezone.utc)
    description = f"Automated snapshot for {volume_id} taken at {now.strftime('%Y-%m-%d %H:%M:%S')}"
    
    # STEP 1: Create a tagged snapshot
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

    # STEP 2: Scan and clean up snapshots older than 30 days
    cutoff_date = now - timedelta(days=retention_days)
    deleted_snapshots = []
    
    try:
        paginator = ec2.get_paginator('describe_snapshots')
        page_iterator = paginator.paginate(
            OwnerIds=['self'],
            Filters=[
                {'Name': f'tag:{tag_key}', 'Values': [tag_value]},
                {'Name': 'volume-id', 'Values': [volume_id]}
            ]
        )
        
        for page in page_iterator:
            for snap in page['Snapshots']:
                snap_id = snap['SnapshotId']
                snap_start_time = snap['StartTime']
                
                if snap_start_time < cutoff_date:
                    logger.info(f"Deleting older snapshot: {snap_id}")
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
```
6. Click the white **Deploy** button on the toolbar to publish your code updates.

<img width="839" height="395" alt="image" src="https://github.com/user-attachments/assets/33432a3d-9a83-4f52-89dd-7c888e7965c8" />

### Configure the Environment Variable

1. While still inside your Lambda function console, click the **Configuration** tab ➔ **Environment variables** sidebar menu item.
2. Click **Edit** ➔ **Add environment variable**.
3. Input the following configuration pair:
   * **Key**: `VOLUME_ID`
   * **Value**: *[Paste your actual EC2 Volume ID copied during Step 1]*
4. Click **Save**.

<img width="625" height="134" alt="image" src="https://github.com/user-attachments/assets/bab43c93-dd1e-46ed-9db0-dd201a9cb0ec" />

## ⏰ Step 4: Configure the EventBridge Weekly Schedule

1. Navigate to the **Amazon EventBridge Console** ➔ **Schedules** ➔ **Create schedule**.
2. Provide a descriptive name such as `Automated_EBS_SnapshotCreation_and_Cleanup`.
3. Set the schedule pattern to a recurring **Cron-based schedule**. Use the weekly cron declaration below to trigger execution every Sunday at midnight UTC:
   ```text
   cron(0 0 ? * SUN *)
   ```
4. Click **Next** to proceed to targets. Choose **AWS Lambda** and pick your `EBS-Weekly-Backup-Cleanup` function from the list. Leave the payload field as an empty JSON block `{}`.
5. Click **Next**. Under the service execution configurations, ensure that you select or modify the trust policy of the assigned schedule execution role to permit EventBridge Scheduler invocation permissions.

### Modify Trust Relationship for Multi-Service Assumption 
To allow your schedule role to hand off processes to both Lambda execution runners and EventBridge system engines seamlessly, modify the **Trust relationships** tab of your execution role in the IAM console to use this configuration:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": [
                    "://amazonaws.com",
                    "://amazonaws.com"
                ]
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```
6. Complete the wizard review steps and click **Create schedule**.

<img width="958" height="127" alt="image" src="https://github.com/user-attachments/assets/32580485-c504-4423-a62e-652d7568beca" />

## 🧪 Step 5: Manual Validation TestingVerify end-to-end functionality using manual testing tools built into the console environment.

1. Open your `EBS-Weekly-Backup-Cleanup` Lambda console page and open the **Test** tab.
2. Keep an empty target event model block `{}` and click the orange **Test** button.
3. Review the green **Execution result: succeeded** block to verify a `200` return response payload alongside logs printing out your real `CREATED SNAPSHOT ID`.

<img width="599" height="317" alt="Execution_response" src="https://github.com/user-attachments/assets/1b0ec0c7-cf5b-46ae-a543-3a5c41e4e98a" />

4. Head back to **EC2 Console** ➔ **Snapshots** to confirm that the new snapshot exists, features your custom descriptive backup name, and includes the tracking meta tag pair: `CreatedBy = Lambda-Backup`.

<img width="958" height="149" alt="Created_snap" src="https://github.com/user-attachments/assets/84ea8bf7-7735-463b-a72c-761a17456ef8" />

## 📊 Architectural Discussion: AWS DLM vs. Custom Lambda

While AWS Data Lifecycle Manager (DLM) manages automated backups natively using built-in lifecycle policies without code overhead, deploying an AWS Lambda function remains the superior choice in the following production use cases:

| Feature Dimension | AWS Data Lifecycle Manager (DLM) | Custom AWS Lambda + Boto3 |
|---|---|---|
| Retention Schemas | Strict count or standard time interval limitations. | Programmatic conditional matrices (e.g., grandfather-father-son backup rotations). |
| Cross-Boundary Execution | Confined within built-in policy capabilities. | Programmatic migration paths across distinct security compliance AWS root accounts. |
| Operational Integrations | Native Amazon CloudWatch metric outputs only. | Integrated multi-destination webhooks (e.g., Slack, Teams, or custom internal APIs). |
| System Fluidity | Independent snapshot process. | Can freeze OS file systems via AWS Systems Manager (SSM) before snapshot creation to maintain transactional database integrity. |


Are there any other infrastructure modules or deployment logs you want to document next, or are we good to go?

