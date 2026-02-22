#!/usr/bin/env python3
"""CLI tool — render a survey.js form interactively and optionally submit or save."""

import argparse
import json
import sys
from pathlib import Path

import requests

# Allow imports from parent package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from forms import DEFAULT_FORM, get_all_elements, load_form, validate_responses


def render_form_cli(form: dict, chat_mode: bool = False) -> dict:
    """Walk through the form in the terminal, collecting responses."""
    print(f"\n{'='*60}")
    print(f"  {form.get('title', 'Survey')}")
    if form.get("description"):
        print(f"  {form['description']}")
    print(f"{'='*60}\n")

    responses: dict = {}
    pages = form.get("pages", [])

    for pi, page in enumerate(pages):
        print(f"--- {page.get('title', f'Page {pi+1}')} ({pi+1}/{len(pages)}) ---\n")

        for el in page.get("elements", []):
            etype = el.get("type", "text")
            name = el["name"]
            title = el.get("title", name)
            required = el.get("isRequired", False)
            req_mark = " *" if required else ""

            if etype in ("text", "comment"):
                val = input(f"  {title}{req_mark}: ")
                responses[name] = val

            elif etype == "radiogroup":
                choices = el.get("choices", [])
                print(f"  {title}{req_mark}:")
                for i, c in enumerate(choices, 1):
                    print(f"    {i}. {c}")
                sel = input("  Select number: ").strip()
                try:
                    responses[name] = choices[int(sel) - 1]
                except (ValueError, IndexError):
                    responses[name] = sel

            elif etype == "checkbox":
                choices = el.get("choices", [])
                print(f"  {title}{req_mark} (comma-separated numbers):")
                for i, c in enumerate(choices, 1):
                    print(f"    {i}. {c}")
                sel = input("  Select: ").strip()
                picked = []
                for s in sel.split(","):
                    s = s.strip()
                    try:
                        picked.append(choices[int(s) - 1])
                    except (ValueError, IndexError):
                        if s:
                            picked.append(s)
                responses[name] = picked

            elif etype == "dropdown":
                choices = el.get("choices", [])
                print(f"  {title}{req_mark}:")
                for i, c in enumerate(choices, 1):
                    print(f"    {i}. {c}")
                sel = input("  Select number: ").strip()
                try:
                    responses[name] = choices[int(sel) - 1]
                except (ValueError, IndexError):
                    responses[name] = sel

            elif etype == "rating":
                lo = el.get("rateMin", 1)
                hi = el.get("rateMax", 5)
                desc_lo = el.get("minRateDescription", "")
                desc_hi = el.get("maxRateDescription", "")
                hint = f" ({lo}={desc_lo}, {hi}={desc_hi})" if desc_lo else ""
                val = input(f"  {title}{req_mark} [{lo}-{hi}]{hint}: ").strip()
                try:
                    responses[name] = int(val)
                except ValueError:
                    responses[name] = val

            elif etype == "boolean":
                val = input(f"  {title}{req_mark} (y/n): ").strip().lower()
                responses[name] = val in ("y", "yes", "true", "1")

            else:
                val = input(f"  {title}{req_mark}: ")
                responses[name] = val

        print()

    return responses


def chat_mode_loop(form: dict, api_url: str | None = None):
    """Simple chat-style interaction: ask each question conversationally."""
    print("\n[Chat Mode] I'll walk you through the form one question at a time.")
    print("Type 'quit' to exit, 'save' to save JSON, 'submit' to send to API.\n")

    responses: dict = {}
    elements = get_all_elements(form)
    idx = 0

    while idx < len(elements):
        el = elements[idx]
        title = el.get("title", el["name"])
        etype = el.get("type", "text")

        # Build prompt
        if etype == "radiogroup":
            choices = el.get("choices", [])
            opts = ", ".join(choices)
            prompt_text = f"Q: {title} (options: {opts})\nA: "
        elif etype == "checkbox":
            choices = el.get("choices", [])
            opts = ", ".join(choices)
            prompt_text = f"Q: {title} (pick multiple, comma-separated from: {opts})\nA: "
        elif etype == "dropdown":
            choices = el.get("choices", [])
            opts = ", ".join(choices)
            prompt_text = f"Q: {title} (choose one: {opts})\nA: "
        elif etype == "rating":
            lo, hi = el.get("rateMin", 1), el.get("rateMax", 5)
            prompt_text = f"Q: {title} (rate {lo}-{hi})\nA: "
        elif etype == "boolean":
            prompt_text = f"Q: {title} (yes/no)\nA: "
        else:
            prompt_text = f"Q: {title}\nA: "

        answer = input(prompt_text).strip()

        if answer.lower() == "quit":
            print("Goodbye.")
            return responses
        if answer.lower() == "save":
            _save_json(responses)
            continue
        if answer.lower() == "submit":
            _submit(responses, form, api_url)
            continue

        # Store
        if etype == "checkbox":
            responses[el["name"]] = [a.strip() for a in answer.split(",")]
        elif etype == "boolean":
            responses[el["name"]] = answer.lower() in ("y", "yes", "true", "1")
        elif etype == "rating":
            try:
                responses[el["name"]] = int(answer)
            except ValueError:
                responses[el["name"]] = answer
        else:
            responses[el["name"]] = answer

        idx += 1

    print("\nAll questions answered!")
    return responses


def _save_json(responses: dict, path: str | None = None):
    if path is None:
        path = "form_responses.json"
    Path(path).write_text(json.dumps(responses, indent=2))
    print(f"Saved to {path}")


def _submit(responses: dict, form: dict, api_url: str | None):
    if not api_url:
        print("No API URL configured. Use --api-url to set one.")
        return
    try:
        r = requests.post(
            f"{api_url}/submit",
            json={"form_id": form.get("title", "default"), "responses": responses},
            timeout=10,
        )
        r.raise_for_status()
        print(f"Submitted! ID: {r.json()['id']}")
    except Exception as exc:
        print(f"Submission failed: {exc}")


def main():
    parser = argparse.ArgumentParser(description="CLI form renderer / chat interface")
    parser.add_argument(
        "--form",
        type=str,
        default=str(DEFAULT_FORM),
        help="Path to survey.js JSON form definition",
    )
    parser.add_argument("--chat", action="store_true", help="Use conversational chat mode")
    parser.add_argument("--api-url", type=str, default=None, help="API URL for submission")
    parser.add_argument("--save", type=str, default=None, help="Save responses to JSON file")
    parser.add_argument("--submit", action="store_true", help="Submit responses to API after completing")
    args = parser.parse_args()

    form = load_form(args.form)

    if args.chat:
        responses = chat_mode_loop(form, api_url=args.api_url)
    else:
        responses = render_form_cli(form)

    if responses:
        errs = validate_responses(form, responses)
        if errs:
            print("\nValidation errors:")
            for e in errs:
                print(f"  - {e}")

        if args.save:
            _save_json(responses, args.save)
        elif not args.submit:
            # Default: ask user what to do
            print("\nResponses collected:")
            print(json.dumps(responses, indent=2))
            choice = input("\n[s]ave JSON / [u]pload to API / [q]uit? ").strip().lower()
            if choice == "s":
                out = input("Filename [form_responses.json]: ").strip() or "form_responses.json"
                _save_json(responses, out)
            elif choice == "u":
                url = args.api_url or input("API URL [http://localhost:8000]: ").strip() or "http://localhost:8000"
                _submit(responses, form, url)

        if args.submit:
            url = args.api_url or "http://localhost:8000"
            _submit(responses, form, url)


if __name__ == "__main__":
    main()
