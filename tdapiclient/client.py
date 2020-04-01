from .accounts import TDAccounts
from .base import TDAuthContext
from .instruments import TDInstruments
from .marketdata import TDMarketdata


class TDClient:
    accounts: TDAccounts
    instruments: TDInstruments
    marketdata: TDMarketdata

    def __init__(self, auth_context: TDAuthContext):
        self.accounts = TDAccounts(auth_context=auth_context)
        self.instruments = TDInstruments(auth_context=auth_context)
        self.marketdata = TDMarketdata(auth_context=auth_context)
