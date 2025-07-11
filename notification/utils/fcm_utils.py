# from pyfcm import FCMNotification

# # Replace this with your actual Firebase server key
# FIREBASE_SERVER_KEY = "YOUR_FIREBASE_SERVER_KEY"

# def send_fcm_notification(token, title, body):
#     push_service = FCMNotification(api_key=FIREBASE_SERVER_KEY)

#     result = push_service.notify_single_device(
#         registration_id=token,
#         message_title=title,
#         message_body=body
#     )

#     return result


import requests

def send_expo_push_notification(token, data=None):
    payload = {
        "to": token,
        "data": data or {},
    }

    headers = {
        "Content-Type": "application/json"
    }

    res = requests.post("https://exp.host/--/api/v2/push/send", json=payload, headers=headers)
    print("Expo response:", res.status_code, res.text)
    return res
