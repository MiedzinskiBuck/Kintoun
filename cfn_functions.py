import boto3
import sys

selected_region = sys.argv[1]
client = boto3.client('cloudformation', region_name=selected_region)
response = client.list_stacks(
        StackStatusFilter=[
            'CREATE_COMPLETE',
            ]
        )

print(response)

StackGivenName = sys.argv[2]
deletion = client.delete_stack(
        StackName=StackGivenName,
        )

print(deletion)
