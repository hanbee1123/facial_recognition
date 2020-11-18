import json
import boto3
from boto3.dynamodb.conditions import Key, Attr



def lambda_handler(event, context):
    print(event['visitors'][0]['unstructured'])
    validation_process(event['visitors'][0]['unstructured'])
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }

def validation_process(event):
    # Validate OTP in dynamodb
    user_otp = event['OTP']
    otp_verification_result  = False
    
    dynamo = boto3.resource('dynamodb')
    table = dynamo.Table('otp')
    filt_exp = Key('otp').eq(int(user_otp))
    response = table.scan(FilterExpression=filt_exp)
    if response['Count']>0:
        otp_verification_result = True
        
    # Validate user information in dynamodb user 
    user_num = event['number']
    num_verification_result = False
    table2 = dynamo.Table('visitors')
    filt_exp2 = Attr('number').eq(user_num)
    response2 = table2.scan(FilterExpression=filt_exp2)
    if response2['Count']>0:
        num_verification_result = True
    print(response2)
    
    # Send result to user
    if num_verification_result == True and otp_verification_result == True:
        message = 'Your number and otp has been verified, you can enter'
    elif num_verification_result == True and otp_verification_result == False:
        message = 'Please check the otp again!'
    elif num_verification_result == False and otp_verification_result ==True:
        message = 'Please check the number again!'
    else:
        message = 'Please check the number and the OTP!!!'
    print(message)    
    sns_to_user(message, user_num)

def sns_to_user(message, number):
    print(message)
    sns = boto3.client('sns')
    response = sns.publish(
        PhoneNumber = number,
        Message = message,
        MessageStructure = 'string'
        )
    print('SNS response', response)
    