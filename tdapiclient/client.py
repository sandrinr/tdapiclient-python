from .accounts import TDAccounts
from .base import TDAuthContext
from .instruments import TDInstruments


class TDClient:
    accounts: TDAccounts
    instruments: TDInstruments

    def __init__(self, auth_context: TDAuthContext):
        self.accounts = TDAccounts(auth_context=auth_context)
        self.instruments = TDInstruments(auth_context=auth_context)
