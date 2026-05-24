# run_eval.py — top-level entry point for the eval suite
#
# Usage:
#   python run_eval.py                    # full dataset (15 questions)
#   python run_eval.py --subset domain    # only domain-category questions
#   python run_eval.py --subset edge      # only edge-case questions
#
# Make sure Phoenix is running in a separate terminal tab before launching:
#   python -c "import phoenix as px; import time; px.launch_app(); [time.sleep(10) for _ in iter(int, 1)]"

import argparse
import asyncio
from src.eval.tracer import init_tracing
from src.eval.runner import run_eval
from src.eval.reporter import report
from src.eval.dataset import get_by_category, get_dataset


def main():
    parser = argparse.ArgumentParser(description="Run the research-agent eval suite.")
    parser.add_argument(
        "--subset",
        type=str,
        default=None,
        help="Run only one category (concept, domain, comparison, relationship, current, edge)",
    )
    args = parser.parse_args()

    # critical: initialize tracing FIRST so guardrail spans and openai calls
    # both flow into the Phoenix instance running in your other terminal tab
    init_tracing()

    if args.subset:
        dataset = get_by_category(args.subset)
        if not dataset:
            print(f"No questions found for category '{args.subset}'")
            return
        print(f"Running subset: {args.subset} ({len(dataset)} questions)")
    else:
        dataset = get_dataset()
        print(f"Running full eval: {len(dataset)} questions")

    # run
    eval_run = asyncio.run(run_eval(subset=dataset))

    # report (writes JSON + markdown, attempts Phoenix dataset upload)
    report(eval_run)


if __name__ == "__main__":
    main()