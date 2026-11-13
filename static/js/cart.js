(() => {
    const cart = document.querySelector("[data-cart]");
    const feedback = cart.querySelector("[data-cart-feedback]");
    const edits = new Map();
    let contents = cart.querySelector("[data-cart-contents]");
    let timer;
    let activeSave;
    let continuing = false;

    function showError(message) {
        feedback.textContent = message;
        feedback.hidden = false;
    }

    function replaceContents(fragment) {
        const focused = document.activeElement;
        const focusedId = focused?.matches("[data-cart-quantity] input[name=quantity]") ? focused.id : null;
        contents.replaceWith(fragment);
        contents = fragment;

        for (const [id, value] of edits) {
            const input = document.getElementById(id);
            if (input) input.value = value;
        }
        if (focusedId) document.getElementById(focusedId)?.focus({ preventScroll: true });
    }

    function nextQuantity() {
        for (const id of edits.keys()) {
            const input = document.getElementById(id);
            if (!input || input.value === input.defaultValue) {
                edits.delete(id);
            } else if (input.validity.valid) {
                return input;
            }
        }
        return null;
    }

    async function saveQuantities() {
        feedback.hidden = true;
        for (let input = nextQuantity(); input; input = nextQuantity()) {
            const { id, value, form } = input;
            edits.delete(id);

            try {
                const response = await fetch(form.action, {
                    method: "POST",
                    body: new FormData(form),
                    headers: { "X-Cart-Partial": "1" },
                });
                if (response.redirected) {
                    window.location.assign(response.url);
                    return false;
                }

                const page = new DOMParser().parseFromString(await response.text(), "text/html");
                const fragment = page.querySelector("[data-cart-contents]");
                if (!fragment) throw new Error("Cart fragment missing");

                if (!response.ok) edits.clear();
                replaceContents(fragment);
                if (!response.ok) return false;
            } catch {
                if (!edits.has(id)) edits.set(id, value);
                showError("Не удалось сохранить количество. Повторите ввод или нажмите Enter.");
                return false;
            }
        }

        if (edits.size) {
            showError("Укажите целое количество от 1 до доступного остатка.");
            return false;
        }
        return true;
    }

    function flush() {
        clearTimeout(timer);
        if (!activeSave) {
            activeSave = saveQuantities().finally(() => { activeSave = null; });
        }
        return activeSave;
    }

    async function continueAfterSave(event, action) {
        if (!activeSave && !edits.size) return;
        event.preventDefault();
        if (continuing) return;

        continuing = true;
        const saved = await flush();
        continuing = false;
        if (saved) action();
    }

    cart.addEventListener("input", (event) => {
        const input = event.target;
        if (!input.matches("[data-cart-quantity] input[name=quantity]")) return;

        edits.set(input.id, input.value);
        clearTimeout(timer);
        timer = setTimeout(flush, 400);
    });

    cart.addEventListener("submit", (event) => {
        const form = event.target;
        if (form.matches("[data-cart-quantity]")) {
            event.preventDefault();
            const input = form.elements.quantity;
            edits.set(input.id, input.value);
            flush();
        } else if (form.matches("[data-cart-remove]")) {
            const action = form.action;
            continueAfterSave(event, () => {
                const current = [...contents.querySelectorAll("[data-cart-remove]")]
                    .find((candidate) => candidate.action === action);
                current?.requestSubmit();
            });
        }
    });

    cart.addEventListener("click", (event) => {
        if (!event.target.closest("[data-cart-checkout]")) return;

        continueAfterSave(event, () => {
            const checkout = contents.querySelector("[data-cart-checkout]");
            if (checkout) window.location.assign(checkout.href);
        });
    });
})();
