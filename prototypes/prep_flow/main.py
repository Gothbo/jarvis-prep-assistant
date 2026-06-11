"""TUI shell for the Prep Flow prototype.

Drives the portable logic module with a lightweight terminal UI.
"""

import sys
import os

from logic import PrepFlow


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def bold(text: str) -> str:
    return f"\x1b[1m{text}\x1b[0m"


def dim(text: str) -> str:
    return f"\x1b[2m{text}\x1b[0m"


def render_header() -> None:
    print(bold("=== JARVIS Prep Flow Prototype ==="))
    print(dim("Answer: Does the end-to-end flow work with our data models?"))
    print()


def render_state(flow: PrepFlow) -> None:
    state = flow.state_dict()
    print(bold("Current State:"))
    print(f"  KB loaded:      {state['kb_loaded']}")
    print(f"  Cases:          {state['case_count']}")
    print(f"  Methodologies:  {state['methodology_count']}")
    print(f"  Sensitivities:  {state['sensitivity_count']}")
    print(f"  Last input:     {state['last_input'] or '(none)'}")
    print(f"  Industry:       {state['detected_industry'] or '(none)'}")
    print(f"  Scenario:       {state['detected_scenario'] or '(none)'}")
    print(f"  Package ready:  {state['package_generated']}")
    if state["error"]:
        print(f"  {bold('Error:')} {state['error']}")
    print()


def render_package(flow: PrepFlow) -> None:
    summary = flow.package_summary()
    if summary is None:
        print(dim("No package generated yet. Type a scenario and press Enter."))
        print()
        return

    print(bold("=== Generated Prep Package ==="))
    print()

    print(bold("[Scenario Assessment]"))
    print(summary["scenario_assessment"])
    print()

    print(bold("[Sensitivity Alerts]"))
    for alert in summary["sensitivity_alerts"]:
        print(f"  - {alert}")
    print()

    print(bold("[Matched Cases]"))
    for case_id in summary["matched_cases"]:
        print(f"  - {case_id}")
    print()

    print(bold("[Follow-up Questions]"))
    for q in summary["follow_up_questions"][:8]:
        print(f"  - {q}")
    print()

    print(bold("[Solution Direction]"))
    print(summary["solution_direction"])
    print()

    print(bold("[Talking Points]"))
    print(summary["talking_points"])
    print()


def render_help() -> None:
    print(dim("Commands:"))
    print("  [Enter scenario]  Generate Prep package")
    print("  c                 Clear last package")
    print("  q                 Quit")
    print()


def main() -> None:
    flow = PrepFlow()

    if not flow.load_knowledge_base():
        print(f"Error: {flow.last_error}")
        sys.exit(1)

    while True:
        clear_screen()
        render_header()
        render_state(flow)
        render_package(flow)
        render_help()

        try:
            user_input = input("Scenario> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nQuitting...")
            break

        if not user_input:
            continue

        if user_input.lower() == "q":
            print("Quitting...")
            break

        if user_input.lower() == "c":
            flow.last_package = None
            flow.last_intent = None
            continue

        # Generate
        with open(os.devnull, "w") as devnull:
            # Temporarily suppress stdout from any library logging
            old_stdout = sys.stdout
            sys.stdout = devnull
            try:
                flow.generate(user_input)
            finally:
                sys.stdout = old_stdout


if __name__ == "__main__":
    main()
