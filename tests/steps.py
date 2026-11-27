from functools import wraps


def step(title):
    def decorate(test):
        @wraps(test)
        def wrapped(self, *args, **kwargs):
            self.test_steps = getattr(self, "test_steps", []) + [title]
            return test(self, *args, **kwargs)

        wrapped.step_title = title
        return wrapped

    return decorate
