from .models import PaymentAttempt


class MockPaymentGateway:
    @staticmethod
    def charge(*, amount, currency, outcome):
        if currency != "RUB" or amount < 0:
            raise ValueError("Некорректные параметры учебного платежа.")
        return PaymentAttempt.Result(outcome)
