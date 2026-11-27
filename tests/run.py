import os
import sys
import time
import unittest

from tests.report import save


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dostavochking.settings")
os.environ.setdefault("DJANGO_SECRET_KEY", "local-test-key-only")
os.environ.setdefault("PAYMENT_PROVIDER", "mock")


class RecordingResult(unittest.TextTestResult):
    def startTest(self, test):
        self._started = time.perf_counter()
        self._outcome = "passed"
        self._detail = ""
        super().startTest(test)

    def addFailure(self, test, error):
        self._outcome = "failed"
        self._detail = self._exc_info_to_string(error, test)
        super().addFailure(test, error)

    def addError(self, test, error):
        self._outcome = "error"
        self._detail = self._exc_info_to_string(error, test)
        super().addError(test, error)

    def addSkip(self, test, reason):
        self._outcome = "skipped"
        self._detail = reason
        super().addSkip(test, reason)

    def stopTest(self, test):
        parts = test.id().split(".")
        self.cases.append({
            "id": test.id(), "layer": parts[1] if len(parts) > 2 else "other",
            "module": parts[2].removeprefix("test_") if len(parts) > 3 else "other",
            "step": getattr(test, "test_steps", [getattr(getattr(test, test._testMethodName), "step_title", test._testMethodName)])[0],
            "status": self._outcome, "duration_ms": round((time.perf_counter() - self._started) * 1000),
            "detail": self._detail,
        })
        super().stopTest(test)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cases = []


class RecordingTextRunner(unittest.TextTestRunner):
    resultclass = RecordingResult
    last_result = None

    def run(self, test):
        result = super().run(test)
        type(self).last_result = result
        return result


def main():
    try:
        import django
        from django.test.runner import DiscoverRunner
    except ImportError as error:
        reason = f"Не установлены зависимости Python: {error}. Выполните python -m pip install -r requirements.txt."
        save({"blocked": True, "reason": reason, "cases": []})
        print(reason, file=sys.stderr)
        return 2

    class ProjectRunner(DiscoverRunner):
        test_runner = RecordingTextRunner

    try:
        django.setup()
        result_code = ProjectRunner(verbosity=2).run_tests(["tests"])
        result = RecordingTextRunner.last_result
        if result is None:
            save({"blocked": True, "reason": "Тестовый запуск остановился до выполнения сценариев.", "cases": []})
            return 2
        save({"blocked": False, "cases": result.cases})
        print("Отчёт: test-results/report.html")
        return 1 if result_code else 0
    except Exception as error:
        save({"blocked": True, "reason": f"Тестовая среда недоступна: {type(error).__name__}: {error}", "cases": []})
        raise


if __name__ == "__main__":
    raise SystemExit(main())
