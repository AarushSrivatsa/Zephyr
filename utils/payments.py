from dodopayments import AsyncDodoPayments
from settings import DODO_API_KEY

dodo = AsyncDodoPayments(
    bearer_token=DODO_API_KEY,
    environment='test_mode' 
)