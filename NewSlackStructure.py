import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv, dotenv_values
import re
import flatten_json as fj
import pandas as pd 
from datetime import datetime

#Global Variables
load_dotenv()

#Connect to slack
api_token=os.getenv("API_TOKEN")
client=WebClient( api_token, "https://app.slack.com/api/")

#Global parameters
channel_id=os.getenv("CHANNEL_ID")
first_day=str(datetime(year=datetime.now().year,month=datetime.now().month,day=1).timestamp())
last_day=str(datetime(year=datetime.now().year,month=datetime.now().month+1,day=1).timestamp())
recognitions_table=pd.DataFrame(columns=['sender_id', 'sender', 'receiver_id','receiver','recognition_type','date'])

def get_user_info(user_id):
    '''
    function to retrieve the user information , such as name surname based on id 
    '''
    try:
        # Call the users.info API method
        response = client.users_info(
            user=user_id,
        )

        user_info = response["user"]
        return user_info
    except SlackApiError as e:
        print(f"Error fetching user info: {e.response['error']}")

def get_list_of_members(channel_id):

    '''
    Function to get the list of members part of a channel , and their respective information
    '''

    try:
        list_of_members_ids=client.conversations_members(channel=channel_id)['members']
        # print('list of members \n',list_of_members_ids)

        '''
        Format : the list_of_members={'id':'name'}
        '''
        list_of_members={}

        for id in list_of_members_ids:
            member_name=get_user_info(id)['name']
            list_of_members.update({id:member_name})

        return list_of_members

    except SlackApiError as e:
        print(f"Error fetching user list: {e.response['error']}")

def get_channel_history(client,channel_id,oldest='',latest=''):
    '''
    Function to get the channel history based on a time period
    '''
    conversation_history=[]
    try:
        if oldest !='' or latest !='':
            result = client.conversations_history(channel=channel_id,oldest=oldest,latest=latest)
        else:
            result = client.conversations_history(channel=channel_id)
        conversation_history = result["messages"]
    except SlackApiError as e:
        print(f"Error: {e}")

    return conversation_history

def check_recognition(recognition):
    if re.search(r'#hardwork',recognition.lower()):
        return 1
        
    elif re.search(r'#perseverance',recognition.lower()) :
        return 2  
    elif re.search(r'#innovation',recognition.lower()) :
        return 3
   
    elif (re.search(r'#supporting(-colleagues?|colleagues?)',recognition.lower()) or recognition.lower() =="#supporting" ) :
        return 4
    elif recognition.lower() in ['#confidence-booster','#confidencebooster','#confidence'] :
        return 5
    else :
        print('Not Right Format',receiver,recognition)


conversation_history = get_channel_history(client=client,channel_id=channel_id,oldest=first_day,latest=last_day)

membersList=get_list_of_members(channel_id)
   

for i,message in enumerate(conversation_history):
    sender=message.get('user')
    time=message.get('ts')
    
    if sender == None or message.get('subtype') in ['channel_join', 'channel_leave']:
        continue 
    #the structure is different when sending pngs or jpgs so we need to skip it /out of our scope for the recognition checks 
    #We are also skipping when joining/leaving the channel as the structure is different

    line= message.get('text').replace('*','')
    receiver=''
    recognition=''
    try:
        if re.search("<@U\w{10}>[^#]*#",line): 
            #note that when used bold structure the text comes differently with ** between the text that is bold 
            blocks=(message.get('blocks')[0]).get('elements')[0]['elements']
            
            len_blocks=len(blocks)
            list_receivers=[]
            for j,x in enumerate(blocks):
                
                # if x.get('type')=='text':
                #     continue
                print('Testing',j,' ---> ',x)
                if x.get('type')=='user' and j<(len_blocks-1):
                    # receiver=membersList.get(x.get('user_id'))
                    receiver=x.get('user_id')
                    recognition=re.search(r"#\w+\S+",blocks[j+1].get('text'))
                    if recognition:
                        recognition=recognition.group()
                        rec_id=check_recognition(recognition=recognition)
                        recognitions_table.loc[len(recognitions_table.index)] = [sender,membersList.get(sender),receiver,membersList.get(receiver),rec_id,time] 

                        
    except IndexError as e:
        print(f"Error: {e}")
    

sorted_df = recognitions_table.sort_values(by=['sender_id', 'date'], ascending=[True, True])
top3_df = sorted_df.groupby('sender_id').head(3)
top3_df.to_csv(f'ResultsForMonth{datetime.now().month}.csv')

