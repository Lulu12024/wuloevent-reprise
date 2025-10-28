import requests

headers = {
    "Accept": "pplication/json",
    "Authorization": "Basic MzYzYjA1MTQtMWIyOS00YzEzLTk4ZWQtZWJjOWZjNTg2ZmMw",
    "Content-Type": "application/json"
}

token = "d1otR6wSSoqFleiqzOeFCx:APA91bEPXHrNZgDfQgeU07fjLMMTa5xvojZH5NZM5zLYkmpnqlYRBixbJHxye8rPicIPOBL8bZDgBWXh1CQWPUglakFu31j5rXeDre9cRt_oqoJKLipwkUbz1g7nz2f6TJtWrdve1ltt"

current_player_id = "8e643d04-046b-4dae-bd88-33db8dc38bd2"

url_notifications = "https://onesignal.com/api/v1/notifications"
url_players = "https://onesignal.com/api/v1/players"

payload = {
    "app_id": "c5a2a150-ab25-4fb9-be01-82bc1a53664a",
    "include_player_ids": ['d65a417b-3103-4fab-a968-29c2ffd51340', current_player_id],
    "contents": {
        "en": "Un nouvel évènement à été publié dans la catégorie \"Sport\" que vous avez ajouté comme favoris."
    },
    "headings": {
        "en": "Nouvel Evènement publié sur Wulo Events"
    },
    "big_picture": "https://i.ibb.co/pdzKtq4/Wulo-Events-Logo.png",
    "huawei_big_picture": "https://i.ibb.co/pdzKtq4/Wulo-Events-Logo.png",
    "data": {"eventPk": 123},
    "buttons": [{"id": "see", "text": "Voir", "icon": "ic_eye"},]
}

response = requests.post(url_notifications, json=payload, headers=headers)

payload = {
    "app_id": "c5a2a150-ab25-4fb9-be01-82bc1a53664a",
    "device_type": 1,
    "identifier": token,
    "tags": {
        "first_name": "Eden",
        "last_name": "HOUNDONOUGBO",
    },
    "amount_spent": "100.99",
    "playtime": 600,
    "notification_types": 1
}

# response = requests.put(url_players + "/8e643d04-046b-4dae-bd88-33db8dc38bd2", json=payload, headers=headers)
# response = requests.get(
#     url_players, params={"app_id": "c5a2a150-ab25-4fb9-be01-82bc1a53664a"}, headers=headers)
# response = requests.delete(url_players + "/d65a417b-3103-4fab-a968-29c2ffd51340", params={"app_id": "c5a2a150-ab25-4fb9-be01-82bc1a53664a"}, headers=headers)
