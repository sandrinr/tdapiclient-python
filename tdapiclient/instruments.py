from .base import TDBase


class TDInstruments(TDBase):
    def search_instruments(self, symbol: str, projection: str):
        res, _ = self._get(
            path=f"/instruments", params={"symbol": symbol, "projection": projection}
        )
        return res
