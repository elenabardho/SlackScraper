import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv, dotenv_values
import re
import flatten_json as fj
import pandas as pd 
from datetime import datetime

# Global variables
load_dotenv()
api_token=os.getenv("API_TOKEN")
client=WebClient( api_token, "https://app.slack.com/api/")
channel_id=os.getenv("CHANNEL_ID")
print(channel_id)
month=int(input('Enter the month you want to calculate recognitions for :'))
first_day=str(datetime(year=datetime.now().year,month=month,day=2).timestamp())
last_day=str(datetime(year=datetime.now().year,month=month+1,day=1).timestamp())
trackSenders={}
list_receivers=[]
bad_regognitions=[]

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


def get_channel_history_current_month(client,channel_id):
    '''
    Function to retrieve channel history of the current month
    '''
    return get_channel_history(client,channel_id,first_day,last_day)
    

def create_initial_scoreTable():

    lom=get_list_of_members(channel_id=channel_id)
    scoreTable={'receiver':['#hardwork','#perseverance','#innovation','#supportingcolleagues','#confidence-booster']}
    
    for member in lom:
        scoreTable.update({member:[0,0,0,0,0]})
    
    return scoreTable


def add_scores(scoreTable,receiver,recognition,sender):

    recognitionGiven=len(trackSenders.get(sender))
    #check the sender is not good logic ?
    bad_regognitions=[]
    
    print('INSIDE METHOD receiver',receiver,'recognition',recognition,'rec Given ',recognitionGiven,' by ',trackSenders.get(sender))
    
    if re.search(r'#hardwork',recognition.lower())  and recognitionGiven<=5:
        scoreTable.get(receiver)[0]+=1
        print('Total Scores so far',scoreTable.get(receiver))
        
    elif re.search(r'#perseverance',recognition.lower())  and recognitionGiven<=5:
        scoreTable.get(receiver)[1]+=1
        print('Total Scores so far',scoreTable.get(receiver))
   
    elif re.search(r'#innovation',recognition.lower())  and recognitionGiven<=5:
        scoreTable.get(receiver)[2]+=1
        print('Total Scores so far',scoreTable.get(receiver))
    
    elif (re.search(r'#supporting(-colleagues?|colleagues?)',recognition.lower()) or recognition.lower() =="#supporting" ) and recognitionGiven<=5:
        scoreTable.get(receiver)[3]+=1
        print('Total Scores so far',scoreTable.get(receiver))
    
   # elif recognition.lower() in ['#confidence-booster','#confidencebooster','#confidence'] and recognitionGiven<=5:
    elif (re.search(r'#supporting(-booster?|booster?)',recognition.lower()) or recognition.lower() =="#confidence" ) and recognitionGiven<=5:
        scoreTable.get(receiver)[4]+=1
        print('Total Scores so far',scoreTable.get(receiver))
    
    else:
        bad_regognitions.append([receiver,recognition])

    
def update_recognition(receiver,recognition,sender,scoreTable):

    # print('The next block',blocks[j+1].get('text'))
    membersList=get_list_of_members(channel_id)
    if recognition :
        recognition=recognition.group()
        
        trackSenders.get(sender).append(receiver)
        
        add_scores(scoreTable=scoreTable,receiver=receiver,recognition=recognition,sender=sender)
        
        print('ADD SCORES',membersList.get(receiver),receiver,'RECOGNITION',recognition,'track senders list of receivers',trackSenders.get(sender))
        
        while list_receivers:

            p=list_receivers.pop()
            trackSenders.get(sender).append(receiver)
            
            
            add_scores(scoreTable=scoreTable,receiver=p,recognition=recognition,sender=sender)
            
            print('ADD SCORES',membersList.get(p),p,'RECOGNITION',recognition)
        
            
    else:
        list_receivers.append(receiver)
        print('List of receivers',list_receivers)
        

def process_message_block(conversation_history):

    
    scoreTable=create_initial_scoreTable()
    membersList=get_list_of_members(channel_id)

    for i,message in enumerate(conversation_history):
        sender=message.get('user')
            
        if sender == None or message.get('subtype') in ['channel_join', 'channel_leave']:
            continue 
        #the structure is different when sending pngs or jpgs so we need to skip it /out of our scope for the recognition checks 
        #We are also skipping when joining/leaving the channel as the structure is different
        
        if sender not in trackSenders.keys():
            trackSenders.update({sender:[]})

        line= message.get('text').replace('*','')
        receiver=''
        recognition=''
        try:
            if re.search("<@U\w{10}>[^#]*#",line): 
                #note that when used bold structure the text comes differently with ** between the text that is bold 
                print('User: ',sender,'\nText\n',line)
                blocks=(message.get('blocks')[0]).get('elements')[0]['elements']
                len_blocks=len(blocks)
                
                for j,x in enumerate(blocks):
                    print('Testing',j,' ---> ',x)
                    
                    if x.get('type')=='user' and j<(len_blocks-1):
                        
                        receiver=x.get('user_id')
                        recognition=re.search(r"#\w+\S+",blocks[j+1].get('text'))
                        update_recognition(receiver=receiver,recognition=recognition,sender=sender,scoreTable=scoreTable)
                        # print('RECEIVER ',membersList.get(receiver),receiver,'RECOGNITION',recognition)
                
        except IndexError as e:
            print(f"Error: {e}")

    return scoreTable
  

def results_to_csv(scoreTable):
    
    columns1=scoreTable.pop('receiver')

    membersList=get_list_of_members(channel_id)
   
    df_recognitions_received=pd.DataFrame(data=scoreTable,index=columns1).transpose()

    df_recognitions_received['name']=df_recognitions_received.index.map(membersList)

    df_recognitions_received.to_csv('FinalResults.csv')

    print(df_recognitions_received)


if __name__=='__main__':
    
    
    conversation_history = get_channel_history_current_month(client=client,channel_id=channel_id)
    membersList=get_list_of_members(channel_id)
    # print(membersList)

    u=get_user_info('U06RXTUM8DP')

    # scoreTable=create_initial_scoreTable()
    
    scoreTable=process_message_block(conversation_history=conversation_history)
   # print('the dictionary \n',scoreTable)  
     
    '''
    Testing code 
    '''
    results_to_csv(scoreTable=scoreTable)
    
    for receiver,scores in scoreTable.items():
        print('\n FINAL RESULTS \n',membersList.get(receiver),scores)
    
    for sender,list in trackSenders.items():
        print('sender',sender,list)
   
    print('BAD RECOGNITIONS')
    print('CONVO LENGTH',len(conversation_history))
 
