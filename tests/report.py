import ast
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "test-results"
JSON_PATH = ARTIFACTS / "results.json"
HTML_PATH = ARTIFACTS / "report.html"
PRESENTATION_PATH = ARTIFACTS / "presentation.html"


def save(data):
    ARTIFACTS.mkdir(exist_ok=True)
    data.setdefault("generated_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    data.setdefault("planned", planned_scenarios())
    JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    HTML_PATH.write_text(render(data), encoding="utf-8")
    PRESENTATION_PATH.write_text(render_presentation(data), encoding="utf-8")


def planned_scenarios():
    planned = {}
    for layer in ("unit", "integration", "e2e"):
        planned[layer] = sum(
            1
            for path in (ROOT / "tests" / layer).glob("test_*.py")
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
        )
    return planned


def render_presentation(data):
    cases = data.get("cases", [])
    counts = Counter(case["status"] for case in cases)
    groups = defaultdict(Counter)
    for case in cases:
        groups[case["layer"]][case["status"]] += 1
    blocked = data.get("blocked", False)
    headline = "Запуск пока недоступен" if blocked else f"{counts['passed']} из {len(cases)} сценариев пройдено"
    reason = escape(data.get("reason", ""))
    layer_names = {"unit": "Модульные", "integration": "Интеграционные", "e2e": "Сквозные HTTP"}
    planned = data.get("planned", {})
    layer_cards = "".join(
        f'<article><h3>{name}</h3><div class="big">{planned.get(key, 0)}</div><div class="track"><i style="width:{(groups[key]["passed"] / max(planned.get(key, 0), 1)) * 100:.1f}%"></i></div><small>подготовлено · {sum(groups[key].values())} выполнено · {groups[key]["passed"]} успешно</small></article>'
        for key, name in layer_names.items()
    )
    examples = [case for case in cases if case["status"] == "passed"][:5]
    example_rows = "".join(f'<li><span>{escape(case["step"])}</span><b>✓</b></li>' for case in examples)
    if not example_rows:
        example_rows = '<li><span>Результаты появятся после запуска в среде с Django и PostgreSQL.</span></li>'
    summary = escape("Запуск прерван до выполнения тестов" if blocked else "Результат сформирован из реального прогона")
    return f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Автотесты · презентация</title><style>
:root{{font-family:Arial,sans-serif;background:#f6f7f4;color:#202821}}*{{box-sizing:border-box}}body{{margin:0}}nav{{position:fixed;top:0;left:0;right:0;height:56px;background:#f6f7f4;border-bottom:1px solid #dce1da;display:flex;align-items:center;justify-content:space-between;padding:0 5%;z-index:2;font-size:13px}}nav a{{color:#2c654b;text-decoration:none}}section{{min-height:100vh;padding:110px max(5%,calc((100vw - 1050px)/2)) 70px;display:flex;flex-direction:column;justify-content:center;border-bottom:1px solid #dce1da}}.label{{color:#69796d;text-transform:uppercase;letter-spacing:.15em;font-size:12px}}h1{{font-size:clamp(42px,7vw,78px);letter-spacing:-.055em;line-height:1.05;margin:22px 0}}h2{{font-size:clamp(30px,4vw,50px);letter-spacing:-.04em;margin:16px 0 30px}}p{{font-size:20px;line-height:1.5;color:#56645a;max-width:720px}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:24px}}article{{background:#fff;border:1px solid #dce1da;border-radius:8px;padding:28px}}h3{{font-size:17px;font-weight:500;margin:0}}.big{{font-size:64px;letter-spacing:-.06em;margin:22px 0}}.track{{height:13px;background:#e9ede7;border-radius:3px;overflow:hidden}}.track i{{display:block;height:100%;background:#27805a}}small{{display:block;color:#69796d;margin-top:12px}}ul{{padding:0;list-style:none;max-width:850px}}li{{display:flex;justify-content:space-between;gap:20px;padding:20px 0;border-bottom:1px solid #dce1da;font-size:18px}}li b{{color:#27805a}}.note{{border-left:3px solid #a68a49;padding-left:20px;margin-top:26px}}.foot{{font-size:13px}}@media(max-width:650px){{.cards{{grid-template-columns:1fr}}section{{padding-top:90px}}}}
</style></head><body><nav><span>ДоставоЧкинг / автотесты</span><a href="report.html">Полный отчёт ↗</a></nav>
<section><div class="label">01 / итог</div><h1>{headline}</h1><p>{summary}</p>{f'<p class="note">{reason}</p>' if reason else ''}<p class="foot">Источник: results.json · {escape(data.get("generated_at", ""))}</p></section>
<section><div class="label">02 / слои</div><h2>Что подготовлено</h2><div class="cards">{layer_cards}</div><p>Полоса показывает долю успешных проверок среди подготовленных в каждом слое.</p></section>
<section><div class="label">03 / примеры</div><h2>Подтверждённые сценарии</h2><ul>{example_rows}</ul><p class="foot">Полный список, статусы и диагностика — в <a href="report.html">отчёте</a>.</p></section>
</body></html>'''


def render(data):
    cases = data.get("cases", [])
    counts = Counter(case["status"] for case in cases)
    total = len(cases)
    groups = defaultdict(Counter)
    for case in cases:
        groups[case["layer"]][case["status"]] += 1
    labels = {"passed": "Пройдено", "failed": "Ошибка", "error": "Сбой", "skipped": "Пропущено"}
    colors = {"passed": "#27805a", "failed": "#bd4b3d", "error": "#bd4b3d", "skipped": "#a68a49"}
    status = "Запуск не состоялся" if data.get("blocked") else ("Все проверки пройдены" if total and counts["passed"] == total else "Есть непройденные проверки")
    cards = "".join(f'<div class="metric"><b>{counts[key]}</b><span>{labels[key]}</span></div>' for key in labels)
    bars = []
    for layer in ("unit", "integration", "e2e"):
        layer_count = groups[layer]
        width = max(sum(layer_count.values()), 1)
        segments = "".join(
            f'<span style="width:{layer_count[key] / width * 100:.2f}%;background:{colors[key]}"></span>'
            for key in labels if layer_count[key]
        )
        bars.append(f'<div class="bar-row"><span>{layer}</span><div class="bar">{segments}</div><strong>{sum(layer_count.values())}</strong></div>')
    rows = "".join(
        f'<tr><td>{escape(case["layer"])}</td><td>{escape(case["module"])}</td>'
        f'<td>{escape(case["step"])}</td><td class="{escape(case["status"])}">{escape(labels.get(case["status"], case["status"]))}</td>'
        f'<td>{case.get("duration_ms", 0)} мс</td></tr>'
        for case in cases
    )
    if not rows:
        rows = '<tr><td colspan="5" class="empty">Нет выполненных тестов</td></tr>'
    issue = escape(data.get("reason", ""))
    issue_block = f'<div class="notice"><strong>Ограничение среды</strong><p>{issue}</p></div>' if issue else ""
    failures = "".join(
        f'<details><summary>{escape(case["step"])} — {escape(case["status"])}</summary><pre>{escape(case.get("detail", ""))}</pre></details>'
        for case in cases if case["status"] in {"failed", "error"}
    )
    generated = escape(data.get("generated_at", ""))
    planned = data.get("planned", {})
    planned_total = sum(planned.values())
    return f'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Автотесты · ДоставоЧкинг</title>
<style>
:root{{font-family:Arial,sans-serif;color:#202821;background:#f7f8f5}}*{{box-sizing:border-box}}body{{margin:0}}main{{max-width:1080px;margin:auto;padding:48px 24px 80px}}header{{border-bottom:1px solid #d9ded7;padding-bottom:30px;margin-bottom:34px}}.eyebrow{{font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#65756a}}h1{{font-size:clamp(30px,5vw,52px);line-height:1.08;letter-spacing:-.04em;margin:14px 0}}h2{{font-size:20px;margin:0 0 18px}}p{{line-height:1.5;color:#556158}}.lead{{font-size:18px;margin:0}}.meta{{font-size:13px;margin-top:20px}}section{{margin:36px 0}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.metric,.panel{{background:white;border:1px solid #dce2da;border-radius:8px}}.metric{{padding:22px}}.metric b{{display:block;font-size:34px;font-weight:600}}.metric span{{font-size:13px;color:#637168}}.panel{{padding:24px}}.bar-row{{display:grid;grid-template-columns:100px 1fr 35px;align-items:center;gap:16px;margin:18px 0;font-size:14px}}.bar{{height:16px;background:#edf0eb;border-radius:3px;display:flex;overflow:hidden}}.bar span{{height:100%}}.bar-row strong{{text-align:right}}.notice{{background:#fff8e7;border-left:3px solid #a68a49;padding:18px 22px;margin:28px 0}}.notice p{{margin:8px 0 0}}.table-wrap{{overflow:auto}}table{{width:100%;border-collapse:collapse;font-size:14px}}th{{text-align:left;color:#65756a;font-weight:500}}td,th{{padding:13px 10px;border-bottom:1px solid #e3e8e1;vertical-align:top}}td.passed{{color:#27805a;font-weight:600}}td.failed,td.error{{color:#bd4b3d;font-weight:600}}td.skipped{{color:#9a803e}}.empty{{color:#7d887f;text-align:center;padding:36px}}details{{border-bottom:1px solid #e3e8e1;padding:15px 0}}summary{{cursor:pointer}}pre{{overflow:auto;white-space:pre-wrap;font-size:12px;background:#f4f5f2;padding:16px}}footer{{font-size:12px;color:#7b867d;margin-top:42px}}@media(max-width:650px){{.metrics{{grid-template-columns:repeat(2,1fr)}}.bar-row{{grid-template-columns:80px 1fr 25px;gap:8px}}}}
</style></head><body><main>
<header><div class="eyebrow">ДоставоЧкинг / качество</div><h1>Результаты автотестов</h1><p class="lead">{status}</p><div class="meta">Сформировано: {generated}</div></header>
{issue_block}
<section><h2>Итог запуска</h2><p>Подготовлено {planned_total} сценариев; выполнено {total}.</p><div class="metrics">{cards}</div></section>
<section class="panel"><h2>Покрытие по слоям</h2>{''.join(bars)}<p>Длина полосы показывает число выполненных сценариев; цвет — их результат.</p></section>
<section class="panel"><h2>Сценарии</h2><div class="table-wrap"><table><thead><tr><th>Слой</th><th>Модуль</th><th>Проверка</th><th>Результат</th><th>Время</th></tr></thead><tbody>{rows}</tbody></table></div></section>
{f'<section class="panel"><h2>Диагностика</h2>{failures}</section>' if failures else ''}
<footer>Источник данных: results.json · тестовые платежи используют локальный mock-шлюз.</footer>
</main></body></html>'''
