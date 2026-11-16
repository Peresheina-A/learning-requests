"""Ручная оценка настоящей модели. Не входит в CI и не создаёт заявки."""

import json
from pathlib import Path
import sys
import time

from llm import LLMError, suggest_fields


def main() -> int:
    cases = json.loads(Path(__file__).with_name("eval_cases.json").read_text(encoding="utf-8"))
    passed = 0
    for case in cases:
        started = time.monotonic()
        try:
            result = suggest_fields(case["text"])
            ok = result.tool.casefold() == case["tool"].casefold()
            if case.get("reason_empty"):
                ok = ok and result.reason == ""
            else:
                ok = ok and case["reason_contains"] in result.reason.casefold()
            passed += int(ok)
            print(json.dumps({
                "passed": ok, "text": case["text"], **result.model_dump(),
                "seconds": round(time.monotonic() - started, 1),
            }, ensure_ascii=False), flush=True)
        except LLMError as error:
            print(json.dumps({"passed": False, "text": case["text"], "error": str(error)},
                             ensure_ascii=False), flush=True)
    print(f"Passed: {passed}/{len(cases)}")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
