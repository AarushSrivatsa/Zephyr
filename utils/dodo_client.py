from dodopayments import AsyncDodoPayments
from settings import DODO_API_KEY, DODO_WEBHOOK_KEY

dodo = AsyncDodoPayments(
    bearer_token=DODO_API_KEY,
    environment='test_mode',
    webhook_key=DODO_WEBHOOK_KEY
)

