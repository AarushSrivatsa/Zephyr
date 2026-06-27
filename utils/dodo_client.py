from dodopayments import AsyncDodoPayments
from settings import DODO_API_KEY, DODO_WEBHOOK_SECRET

dodo = AsyncDodoPayments(
    bearer_token=DODO_API_KEY,
    environment='test_mode',
    webhook_key=DODO_WEBHOOK_SECRET
)

