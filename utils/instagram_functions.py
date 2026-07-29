from utils.http_client import client

async def send_dm(ig_user_id: str, comment_id: str, message: str, access_token: str):
    response = await client.post(
        f'https://graph.instagram.com/v25.0/{ig_user_id}/messages',
        json={
            'recipient': {'comment_id': comment_id},
            'message': {'text': message}
        },
        params={'access_token': access_token}
    )
    if response.status_code != 200:
        print(f'DM failed: {response.text}')
    else:
        print(f'DM sent for comment {comment_id}')


async def send_reply(comment_id: str, message: str, access_token: str):
    response = await client.post(
        f'https://graph.instagram.com/v25.0/{comment_id}/replies',
        params={'message': message, 'access_token': access_token}
    )
    if response.status_code != 200:
        print(f'Reply failed: {response.text}')
    else:
        print(f'Reply sent for comment {comment_id}')