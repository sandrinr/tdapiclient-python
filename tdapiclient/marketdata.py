import collections.abc
import datetime
from typing import Sequence, Union

from .base import TDBase


class TDMarketdata(TDBase):
    # pylint: disable=unused-argument
    def get_option_chain(
        self,
        symbol: str,
        contract_type: str = None,
        strike_count: int = None,
        strategy: str = None,
        interval: str = None,
        strike: str = None,
        range_: str = None,
        from_date: datetime.date = None,
        to_date: datetime.date = None,
        volatility: str = None,
        underlying_price: str = None,
        interest_rate: str = None,
        days_to_expiration: int = None,
        exp_month: str = None,
        option_type: str = None,
        apikey: str = None,
    ):
        params = self.params_from_locals(locals())
        res, _ = self._get(path=f"/marketdata/chains", params=params)
        return res

    def get_quotes(self, symbol: Union[str, Sequence[str]], apikey: str = None):
        if not isinstance(symbol, str) and isinstance(symbol, collections.abc.Sequence):
            symbol = ",".join(symbol)
        params = self.params_from_locals(locals())
        res, _ = self._get(path=f"/marketdata/quotes", params=params)
        return res
