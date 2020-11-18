import json
import base64
import random
import boto3
import cv2
import uuid
import time
from boto3.dynamodb.conditions import Key

STREAM_ARN = 'arn:aws:kinesisvideo:us-east-1:608484589071:stream/smart_door_hbl258/1604736950266'

dynamo_db_client = boto3.client('dynamodb')
sns_client = boto3.client('sns')
kvs_client = boto3.client('kinesisvideo')
dynamodb_resource = boto3.resource('dynamodb')
rekognition_client = boto3.client('rekognition')


# Lambda handler passes the event Records to the record_processor function

  

def lambda_handler(event, context):
    record_processor(event['Records'])

    return {
        'statusCode': 200,
        'body': json.dumps('Data being processed')
    }

def record_processor(records):
    person_detected = False
    for record in records:
        if person_detected == True:
            break
        encoded_data = record['kinesis']['data']
        temp_decode = base64.b64decode(encoded_data)
        decoded_data = json.loads(temp_decode)
       

        face_search_response = decoded_data['FaceSearchResponse']
        #Loop until face is detected
        if len(face_search_response) > 0:
            print("face detected")
            person_detected = True
        else:
            print("No face detected yet")
            continue
        
    #check if he/she is a registered person
    # If registered, run registered_person_process
    for face_search in face_search_response:
        try:
            face_search['MatchedFaces']
            print("matched face is detected")
            face_id = face_search['MatchedFaces'][0]['Face']['FaceId']
            registered_person_process(face_id)
            break
    # If not registered, run unregistered_person_process
        except:
          print("unmatched face is detected")
          unknown_face = face_search['DetectedFace']
          fragment_number = decoded_data['InputInformation']['KinesisVideo']['FragmentNumber']
          unregistered_person_process(unknown_face, fragment_number)
    
def registered_person_process(face_id):
    print("Running registered person process")
    #Double check if face id is in DynamoDB
    table = dynamodb_resource.Table('visitors')
    filtering_exp = Key('face_id').eq(face_id)
    response = table.scan(FilterExpression=filtering_exp)
    print(response)
    
    #If id_exists, create OTP and send message
    if response['Count'] > 0:
        otp = create_otp()
        print("OTP is" , otp)
        phone_number = response['Items'][0]['number']
        print("phone_number is ", phone_number)
        
        # Insert the OTP to dynamodb
        insert_otp_to_db(face_id, otp)
        
        #Send message to visitor
        message = f'You are verified, type in your OTP: {otp}'
        # sms_to_visitor(message, phone_number, otp)
    else:
        #Send message to not verified customer
        message = 'You are NOT verified, wait until owner approves entrace'
        # sms_to_visitor(message, phone_number, otp)

#If visitor is unregistered, we extract the image and save it in s3.
# The link of s3 will be sent to owner to decide whether to approve visitor or not
def unregistered_person_process(unknown_face, fragment_number):
    temp_location = f"/tmp/{str(uuid.uuid1())}"
    loop = True
    print('running NOT registered person process')
    #upload KVS capture to S3
    endpoint = kvs_client.get_data_endpoint(
        StreamARN=STREAM_ARN,
        APIName='GET_MEDIA'

    )['DataEndpoint']
    print('DataEndPoint:', endpoint)
    
    kvm = boto3.client('kinesis-video-media', endpoint_url = endpoint, region_name='us-east-1')
    kvm_stream = kvm.get_media(
        StreamARN=STREAM_ARN,
        StartSelector={'StartSelectorType': 'FRAGMENT_NUMBER', 'AfterFragmentNumber': fragment_number}
    )
    with open(f"{temp_location}.mkv", 'wb') as f:
        streamBody = kvm_stream['Payload'].read(1024 * 2048)  
        f.write(streamBody)
        cap = cv2.VideoCapture(f"{temp_location}.mkv")
        ret, frame = cap.read()
        all_frames = []
        cv2.imwrite(f"{temp_location}.jpeg", frame)
        s3_client = boto3.client('s3')
        s3_client.upload_file(
            f"{temp_location}.jpeg",
            "smart-door-hbl258",  
            f'frame_{temp_location}.jpeg'
        )
        cap.release()
        print("image successfully sent to S3")
        
    
    link_to_img = f"https://smart-door-hbl258.s3.amazonaws.com/frame_{temp_location}.jpeg"
    message = f"The image is in the link {link_to_img}. Please approve or NOT"
    
    
    while loop == True:
        queue_message(message)
        sms_to_owner(message)
        loop = False
    

    
#__________________________________HELPER FUNCTIONS___________________________________
def queue_message(message):
    sqs = boto3.client(
        service_name = 'sqs',
        region_name='us-east-1'
        )

    response = sqs.send_message(
        QueueUrl = 'https://sqs.us-east-1.amazonaws.com/608484589071/face_image',
        MessageBody=str(message)
        )
    print('FaceID enqueued')

def sms_to_owner(message):
    response = sns_client.publish(
        PhoneNumber="+821028293179",
        Message=message,
        MessageStructure='string'
        )
    print('SNS response!!', response)
    
def sms_to_visitor(message, phone_number, otp):
    response = sns_client.publish(
        PhoneNumber = phone_number,
        Message = message,
        MessageStructure = 'string'
        )
    print('SNS response!', response)


def insert_otp_to_db(face_id, otp):
    time_limit = int(time.time()) +5 *60
    table = dynamodb_resource.Table('otp')
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