import ujson
import json
from dclibs import queuer, logs, rabbitmq_utils, config, rediscache, sfapi, postgres, utils, aws
LOGGER = logs.LOGGER

### SERVICE TEMPLATE
SERVICE_NAME='bulkservice'
SERVICE_DESCRIPTION="Insert large amount of data usinb BULK V2 API."
SERVICE_LABEL="Mass Data insert into Salesforce."
SERVICE_ATTRIBUTES=[
        {'AttributeName':'S3Url', 'AttributeLabel': 'File URL', 'AttributeDescription':'URL to retrieve the CSV content'},
        {'AttributeName':'CSVStructure', 'AttributeLabel': 'CSV Header', 'AttributeDescription':'Comma separated list of fields in the CSV file'},
        {'AttributeName':'SFObjectName', 'AttributeLabel': 'Salesforce Object Name', 'AttributeDescription':'Salesforce Object name the data must be inserted in (Account, ...)'}
    ]
SERVICE_STRUCTURE = {'ServiceName':SERVICE_NAME,
    'ServiceLabel':SERVICE_LABEL,
    'ServiceDescription':SERVICE_DESCRIPTION,
    'ServiceAttributes' : SERVICE_ATTRIBUTES,
    'PublishExternally':True}
###


def bulkSend(S3Url, CSVStructure, SFObjectName, dictValue):
    localfilename = aws.getData(S3Url)
    sfapi.Bulkv2_INSERT(localfilename, CSVStructure, SFObjectName)

def treatMessage(dictValue):
    LOGGER.info(dictValue)
    # notifies the user the service starts treating
    utils.serviceTracesAndNotifies(dictValue, SERVICE_NAME, SERVICE_NAME + ' - Process Started', True)
    # check if the message was comoing from a PE
    S3Url = ''
    CSVStructure = ''
    SFObjectName = ''

    if ('data' in dictValue):
        if ('payload' in dictValue['data']):
            if ("S3Url" in dictValue['data']['payload']):
                S3Url = dictValue['data']['payload']['S3Url']
                CSVStructure = dictValue['data']['payload']['CSVStructure']
                SFObjectName = dictValue['data']['payload']['SFObjectName']
    if (S3Url == ''): #means nothing was found
        S3Url = dictValue['S3Url']
        CSVStructure = dictValue['CSVStructure']
        SFObjectName = dictValue['SFObjectName']    
    
    
    bulkSend(S3Url, CSVStructure, SFObjectName, dictValue)
    utils.serviceTracesAndNotifies(dictValue, SERVICE_NAME, SERVICE_NAME + ' - Process Ended', True)
    
def genericCallback(ch, method, properties, body):
    try:
        # transforms body into dict
        treatMessage(ujson.loads(body))
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        LOGGER.error(e.__str__())

def announce():
    # sends a message to the proper rabbit mq queue to announce himself
    queuer.sendToQueuer(SERVICE_STRUCTURE, config.SERVICE_REGISTRATION)    

if __name__ == "__main__":
    queuer.initQueuer()
    announce()
    queuer.listenToTopic(config.SUBSCRIBE_CHANNEL, 
    {
        config.QUEUING_KAFKA : treatMessage,
        config.QUEUING_CLOUDAMQP : genericCallback,
    })

