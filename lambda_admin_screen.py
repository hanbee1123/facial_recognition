import json
import random
import boto3
import time

QUEUEURL = 'https://sqs.us-east-1.amazonaws.com/608484589071/face_image'
            

def lambda_handler(event, context):
    body = json.loads(event['body'])
    body2 = body['visitors'][0]['unstructured']
    print(body2)

    visitor_num = body2['phone']
    visitor_name = body2['name']
    visitor_name = visitor_name.replace(" ",",")

    # Dequeue Face Image 
    visitor_face = dequeue_img()
    print('image is at: ', visitor_face)
    
    # Register face in rekognition collections and retrieve face id
    face_id = fetch_face_id(visitor_face)
    print('face_id is: ', face_id)
    
    #Put face id, name, phone in dynamodb
    upload_dynamo(face_id, visitor_name, visitor_num)
    
    #Create and save OTP in dynaodb
    otp = create_otp()
    upload_otp(face_id, otp)
    
    #Send OTP to user
    sns_to_visitor(visitor_name, visitor_num, otp)
    
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
    
def sns_to_visitor(name, number, otp):
    messager = f"Dear {name}, you have been authorized, your OTP is {otp}. http://smart-door-user-page.s3-website-us-east-1.amazonaws.com"
    sns = boto3.client('sns', region_name='us-east-1')
    response = sns.publish(
        PhoneNumber = number,
        Message = messager,
        MessageStructure = 'string'
        )
    print('SNS response is:', response)
    
def upload_otp(face_id, otp):
    time_limit = int(time.time()) +5 *60
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('otp')
    with table.batch_writer() as batch:
        batch.put_item (
            Item = {
            'otp':otp,
            'face_id':face_id,
            'time_limit': time_limit
            }
        )
    print('inserted into dynamodb with time limit ', time_limit)

def create_otp():
    otp = 0
    for i in range(1,4):
        otp += random.randint(0,9)
        otp *= 10
    return otp


def upload_dynamo(face_id, name, number):
    dynaodb = boto3.resource('dynamodb', region_name = 'us-east-1')
    table = dynaodb.Table('visitors')
    try:
        with table.batch_writer() as batch:
            batch.put_item(
                Item = {
                    'face_id':face_id,
                    'name':name,
                    'number':number
                })
        print('SUCCESSFUL UPLOAD TO DYNAMODB')
            
    except:
        print('ERROR UPLAODING TO DB')


def fetch_face_id(img_url):
    rekog = boto3.client('rekognition')
    new_img_url = img_url[43:]
    new_image_name = new_img_url[13:25]
    indexed_face = rekog.index_faces(
            CollectionId = 'smart_door_collection_hbl258',
            Image={'S3Object':{'Bucket': 'smart-door-hbl258','Name':new_img_url}},
            ExternalImageId=new_image_name,
            MaxFaces=1,
            QualityFilter="AUTO",
            DetectionAttributes=['ALL']
            )
    face_id = indexed_face['FaceRecords'][0]['Face']['FaceId']
    return face_id
        


def dequeue_img():
    sqs = boto3.client('sqs', region_name = 'us-east-1')
    try:
        sqs_response = sqs.receive_message(
        QueueUrl = QUEUEURL,
        AttributeNames=[
            'SentTimestamp'
        ],
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            'All'
        ],
        VisibilityTimeout = 0,
        WaitTimeSeconds = 0
        )
        message = sqs_response['Messages'][0]
        message2 = message['Body']
        imageurl = message2
        
        receipt_handle = sqs_response['Messages'][0]['ReceiptHandle']
        sqs.delete_message(
            QueueUrl= QUEUEURL,
            ReceiptHandle=receipt_handle
            )
    except:
        return ("Error while dequeueing")
    
    return(imageurl)
    
