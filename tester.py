import boto3


sns_client = boto3.client('sns', region_name='us-east-1')

def sms_to_owner(message):
    response = sns_client.publish(
        PhoneNumber="+8201028293179",
        Message=message,
        MessageStructure='string'
        )
    print('SNS response!!', response)

if __name__ == "__main__":
    sms_to_owner('whhahsdhawodo')   