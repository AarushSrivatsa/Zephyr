import cloudflare
from settings import CLOUDFLARE_API_TOKEN, R2_ACCOUNT_ID, R2_BUCKET_NAME, R2_PUBLIC_URL
import uuid

cf = cloudflare.AsyncCloudflare(api_token=CLOUDFLARE_API_TOKEN)

async def upload_file(file_bytes: bytes, key: str, content_type: str) -> str:
    await cf.r2.buckets.objects.upload(
        key,
        bucket_name=R2_BUCKET_NAME,
        account_id=R2_ACCOUNT_ID,
        body=file_bytes,
        extra_headers={'Content-Type': content_type}
    )
    return f'{R2_PUBLIC_URL}/{key}'

async def delete_post_media(post):
    for item in post.media_items:
        key = item.media_url.split('.com/')[-1]
        await cf.r2.buckets.objects.delete(
            key,
            bucket_name=R2_BUCKET_NAME,
            account_id=R2_ACCOUNT_ID
        )

def generate_key(user_id: str, filename: str) -> str:
    return f'media/{user_id}/{uuid.uuid4()}_{filename}'