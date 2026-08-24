from dodopayments import AsyncDodoPayments
from settings import DODO_API_KEY, DODO_WEBHOOK_SECRET, DODO_ENVIRONMENT

dodo = AsyncDodoPayments(
    bearer_token=DODO_API_KEY,
    environment=DODO_ENVIRONMENT,
    webhook_key=DODO_WEBHOOK_SECRET
)