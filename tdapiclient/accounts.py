import datetime
from typing import Collection, Union
from urllib.parse import quote as q

from .base import TDBase


class TDAccounts(TDBase):
    def cancel_order(self, account_id: str, order_id: str):
        res, _ = self._delete(path=f"/accounts/{q(account_id)}/orders/{q(order_id)}")
        return res

    def get_order(self, account_id: str, order_id: str):
        res, _ = self._get(path=f"/accounts/{q(account_id)}/orders/{q(order_id)}")
        return res

    def get_orders_by_path(
        self,
        account_id: str,
        from_entered_time: Union[datetime.datetime, datetime.date] = None,
        to_entered_time: Union[datetime.datetime, datetime.date] = None,
        status: str = None,
        max_results: int = None,
    ):
        params = {}
        if from_entered_time is not None:
            params["fromEnteredTime"] = from_entered_time.isoformat()
        if to_entered_time is not None:
            params["toEnteredTime"] = to_entered_time.isoformat()
        if status is not None:
            params["status"] = status
        if max_results is not None:
            params["max_results"] = str(max_results)
        res, _ = self._get(path=f"/accounts/{q(account_id)}/orders", params=params)
        return res

    def place_order(self, account_id: str, order: dict) -> str:
        """Place order and return order ID (if successful)."""
        _, headers = self._post(
            path=f"/accounts/{q(account_id)}/orders",
            json=order,
            expect_response_body=False,
        )
        # The order ID can be found in the Location header
        return headers["Location"].split("/")[-1]

    def replace_order(self, account_id: str, order_id: str, order: dict) -> str:
        """Replace an order and return order ID (if successful)."""
        _, headers = self._put(
            path=f"/accounts/{q(account_id)}/orders/{q(order_id)}",
            json=order,
            expect_response_body=False,
        )
        # The order ID can be found in the Location header
        return headers["Location"].split("/")[-1]

    def get_account(self, account_id: str, fields: Collection[str] = None) -> dict:
        res, _ = self._get(
            path=f"/accounts/{q(account_id)}", params={"fields": ",".join(fields or [])}
        )
        return res

    def get_accounts(self, fields: Collection[str] = None):
        res, _ = self._get(path="/accounts", params={"fields": ",".join(fields or [])})
        return res

    def get_transactions(
        self,
        account_id: str,
        type_: str = None,
        symbol: str = None,
        start_date: datetime.date = None,
        end_date: datetime.date = None,
    ):
        params = {}
        if type_ is not None:
            params["type"] = type_
        if symbol is not None:
            params["symbol"] = symbol
        if start_date is not None:
            params["startDate"] = start_date.isoformat()
        if end_date is not None:
            params["endDate"] = end_date.isoformat()
        res, _ = self._get(
            path=f"/accounts/{q(account_id)}/transactions", params=params
        )
        return res
