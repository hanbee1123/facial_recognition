import boto3

def upload_to_dynamodb():
    dynamodb = boto3.resource('dynamodb', region_name = 'us-east-1')
    table = dynamodb.Table("visitors")
    with table.batch_writer() as batch:
        batch.put_item(
            Item = {
                'face_id' : 'ccd26703-ea6f-4726-9224-d7d653e515c4',
                'name':'Han Bee Lee',
                'number':'+821028293179'
            }
        )

if __name__ == "__main__":
    upload_to_dynamodb()