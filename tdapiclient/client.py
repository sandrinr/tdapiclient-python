from .accounts import TDAccounts
from .base import TDContext
from .instruments import TDInstruments


class TDClient:
    accounts: TDAccounts
    instruments: TDInstruments

    def __init__(self, client_id: str, refresh_token: str, access_token=None):
        context = TDContext(
            client_id=client_id, refresh_token=refresh_token, access_token=access_token
        )
        self.accounts = TDAccounts(context=context)
        self.instruments = TDInstruments(context=context)
