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

async def publish_image(post, access_token: str):
    media_item = post.media_items[0]
    
    # Create container
    response = await client.post(
        f'https://graph.instagram.com/v25.0/{post.user.user_id}/media',
        params={
            'image_url': media_item.media_url,
            'caption': post.caption,
            'access_token': access_token
        }
    )
    container_id = response.json()['id']

    # Publish
    await client.post(
        f'https://graph.instagram.com/v25.0/{post.user.user_id}/media_publish',
        params={
            'creation_id': container_id,
            'access_token': access_token
        }
    )

async def publish_reel(post, access_token: str):
    media_item = post.media_items[0]
    
    # Create container
    response = await client.post(
        f'https://graph.instagram.com/v25.0/{post.user.user_id}/media',
        params={
            'media_type': 'REELS',
            'video_url': media_item.media_url,
            'caption': post.caption,
            'access_token': access_token
        }
    )
    container_id = response.json()['id']

    # Publish
    await client.post(
        f'https://graph.instagram.com/v25.0/{post.user.user_id}/media_publish',
        params={
            'creation_id': container_id,
            'access_token': access_token
        }
    )

async def publish_carousel(post, access_token: str):
    # Step 1: Create individual containers for each media item
    container_ids = []
    for item in sorted(post.media_items, key=lambda x: x.order):
        media_type = 'VIDEO' if 'video' in item.media_type else 'IMAGE'
        params = {
            'media_type': media_type,
            'is_carousel_item': 'true',
            'access_token': access_token
        }
        if media_type == 'VIDEO':
            params['video_url'] = item.media_url
        else:
            params['image_url'] = item.media_url

        response = await client.post(
            f'https://graph.instagram.com/v25.0/{post.user.user_id}/media',
            params=params
        )
        container_ids.append(response.json()['id'])

    # Step 2: Create carousel container
    response = await client.post(
        f'https://graph.instagram.com/v25.0/{post.user.user_id}/media',
        params={
            'media_type': 'CAROUSEL',
            'children': ','.join(container_ids),
            'caption': post.caption,
            'access_token': access_token
        }
    )
    carousel_id = response.json()['id']

    # Step 3: Publish carousel
    await client.post(
        f'https://graph.instagram.com/v25.0/{post.user.user_id}/media_publish',
        params={
            'creation_id': carousel_id,
            'access_token': access_token
        }
    )

