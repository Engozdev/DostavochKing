import base64
import json
from contextlib import closing
from http.client import HTTPException, HTTPSConnection
from urllib.parse import quote

from django.conf import settings


class YooKassaError(Exception):
    pass


class YooKassaGateway:
    @staticmethod
    def _request(method, path, *, payload=None, idempotence_key=None):
        shop_id = getattr(settings, "YOOKASSA_SHOP_ID", "")
        secret_key = getattr(settings, "YOOKASSA_SECRET_KEY", "")
        if not shop_id or not secret_key:
            raise YooKassaError("Укажите идентификатор магазина и секретный ключ ЮKassa.")

        credentials = base64.b64encode(f"{shop_id}:{secret_key}".encode()).decode("ascii")
        headers = {"Authorization": f"Basic {credentials}", "Accept": "application/json"}
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode()
        if idempotence_key is not None:
            headers["Idempotence-Key"] = str(idempotence_key)

        try:
            with closing(HTTPSConnection("api.yookassa.ru", timeout=5)) as connection:
                connection.request(method, path, body=body, headers=headers)
                response = connection.getresponse()
                if not 200 <= response.status < 300:
                    raise YooKassaError("ЮKassa отклонила запрос. Попробуйте ещё раз.")
                data = json.loads(response.read())
        except (OSError, HTTPException):
            raise YooKassaError("ЮKassa временно недоступна. Попробуйте ещё раз.") from None
        except (UnicodeError, json.JSONDecodeError):
            raise YooKassaError("ЮKassa вернула некорректный ответ.") from None

        if not isinstance(data, dict):
            raise YooKassaError("ЮKassa вернула некорректный ответ.")
        return data

    @classmethod
    def ensure_test_shop(cls):
        if cls._request("GET", "/v3/me").get("test") is not True:
            raise YooKassaError("Настройки магазина ЮKassa не соответствуют режиму работы приложения.")

    @classmethod
    def create_payment(cls, *, amount, currency, attempt_key, return_url):
        return cls._request(
            "POST",
            "/v3/payments",
            payload={
                "amount": {"value": f"{amount:.2f}", "currency": currency},
                "capture": True,
                "payment_method_data": {"type": "bank_card"},
                "confirmation": {"type": "redirect", "return_url": return_url},
            },
            idempotence_key=attempt_key,
        )

    @classmethod
    def get_payment(cls, payment_id):
        return cls._request("GET", f"/v3/payments/{quote(str(payment_id), safe='')}")

    @classmethod
    def create_refund(cls, *, payment_id, amount, currency, idempotence_key, description):
        return cls._request(
            "POST",
            "/v3/refunds",
            payload={
                "payment_id": str(payment_id),
                "amount": {"value": f"{amount:.2f}", "currency": currency},
                "description": description,
            },
            idempotence_key=idempotence_key,
        )

    @classmethod
    def get_refund(cls, refund_id):
        return cls._request("GET", f"/v3/refunds/{quote(str(refund_id), safe='')}")
