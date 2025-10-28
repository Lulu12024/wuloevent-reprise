"""
This call sends a message to the given recipient with vars and custom vars.
"""
from dotenv import dotenv_values
from mailjet_rest import Client

environ = dotenv_values(".env")
api_key = environ['MJ_APIKEY_PUBLIC']
api_secret = environ['MJ_APIKEY_PRIVATE']
mailjet = Client(auth=(api_key, api_secret), version='v3.1')

data = {
  'Messages': [
		{
			"From": {
				"Email": "wuloevents@gmail.com",
				"Name": "Wulo Events"
			},
			"To": [
				{
					"Email": "wesleymontcho@gmail.com",
					"Name": "Wesley Eliel MONTCHO"
				}
			],
			"TemplateID": 4465556,
			"TemplateLanguage": True,
			"Subject": "Confirmation de Creation de Compte",
			"Variables": {
    "wuloEventsAccountValidationCode": "555555",
    "wuloEventsAccountValidationCodeExpiryTime": "10 minutes"
  }
		}
	]
}
"""
result = mailjet.send.create(data=data)
print(result.status_code)
print(result.json())


"""
import requests

headers = {
    'Content-Type': 'application/json',
}

json_data = {
    'Messages': [
        {
            'From': {
                'Email': 'wuloevents@gmail.com',
                'Name': 'Wulo Events',
            },
            'To': [
                {
					"Email": "wesleymontcho@gmail.com",
					"Name": "Wesley Eliel MONTCHO"
                },
            ],
            'TemplateID': 4465556,
            'TemplateLanguage': True,
            'Subject': 'Confirmation de Creation de Compte',
            'Variables': {
                'wuloEventsAccountValidationCode': '555555',
                'wuloEventsAccountValidationCodeExpiryTime': '10 minutes',
            },
        },
    ],
}

"""json_data = {
    'Messages': [
        {
            'From': {
                'Email': 'wuloevents@gmail.com',
                'Name': 'Wulo Events',
            },
            'To': [
                {
                    'Email': 'wesleymontcho@gmail.com',
                    'Name': 'Wesley Eliel MONTCHO',
                },
            ],
            'TemplateID': 4465556,
            'TemplateLanguage': True,
            'Subject': 'Confirmation de Creation de Compte',
            'Variables': {
                'wuloEventsAccountValidationCode': '555555',
                'wuloEventsAccountValidationCodeExpiryTime': '10 minutes',
            },
        },
    ],
}"""

response = requests.post(
    'https://api.mailjet.com/v3.1/send',
    headers=headers,
    json=json_data,
    auth=(api_key, api_secret),
)
print(response.json())