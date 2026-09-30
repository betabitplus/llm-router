"""Pin subsumption: which mutation pins of a contract other pins of the contract make redundant.

A mutation pin is written for one mutant, but it often kills its neighbours too: the pins of one
function test the same behaviour from several sides. Every pin of a contract is run against every
mutant the contract's pins pin, which gives the kill matrix, and the pins kept are a greedy set
cover of it (Chvátal's heuristic, the usual one for reducing a suite by the mutants it kills, as in
PRIMG and FoadG's LLM-assisted minimization): each step keeps the pin that kills the most mutants
still uncovered. Every other pin is redundant, since the pins kept kill every mutant it pins.

A pin may also kill a mutant it does not pin, one no other test kills; the matrix cannot see that
without running the whole suite on every mutant of the contract. The campaign run after the
removal is the check: a mutant it caught before and misses now brings back the removed pins that
kill it, found by the same runner. Semantic and rule mutants are both given as whole module
sources, as the cascade judges a pin against its mutant.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Callable
from pathlib import Path

# A mutant whose run does not finish tells which pins kill it no more than a run that crashed.
UNDECIDED = None


def greedy_cover(kills: dict[str, set[str]], universe: set[str], order: list[str]) -> list[str]:
    """The pins kept, in the order they were chosen: each step the pin that kills the most mutants
    still uncovered, a tie going to the pin that kills the most in all and then to the earlier pin
    in ``order``. A mutant no pin kills stays uncovered and keeps no pin."""
    uncovered = {mutant for mutant in universe if any(mutant in kills.get(pin, set()) for pin in order)}
    kept: list[str] = []
    while uncovered:
        best = max(order, key=lambda pin: (len(kills.get(pin, set()) & uncovered), len(kills.get(pin, set())), -order.index(pin)))
        kept.append(best)
        uncovered -= kills.get(best, set())
    return kept


def junit_failures(xml_path: Path) -> set[str] | None:
    """The class paths (a test module's dotted path, and its class when it has one) of the failing or
    erroring test cases in a JUnit report, as pytest names them by default; None without a report."""
    if not xml_path.is_file():
        return None
    return {
        str(case.get("classname") or "")
        for case in ET.parse(xml_path).getroot().iter("testcase")
        if case.find("failure") is not None or case.find("error") is not None
    }


def module_of(pin: str) -> str:
    """A test file's dotted path, as pytest's class path begins with it."""
    return pin.removesuffix(".py").replace("/", ".")


def pins_failing(workdir: Path, pins: list[str], run_tests: Callable[..., dict], timeout: int) -> set[str] | None:
    """The pins that fail in one run of them all in the copy, each to the end (no first-failure
    stop); None when the run did not finish or pytest could not run the pins."""
    report = workdir / ".pin-subsumption.xml"
    report.unlink(missing_ok=True)
    run = run_tests(workdir, [*pins, f"--junitxml={report}"], timeout)
    failed = junit_failures(report)
    report.unlink(missing_ok=True)
    if run.get("returncode") not in (0, 1) or failed is None:
        return UNDECIDED
    return {pin for pin in pins if any(name == module_of(pin) or name.startswith(module_of(pin) + ".") for name in failed)}


def kill_matrix(workdir: Path, pins: list[str], mutants: dict[str, tuple[str, str]], run_tests: Callable[..., dict], timeout: int = 300) -> dict[str, set[str] | None]:
    """For each mutant, given as the file it changes (relative to the copy) and that file's mutated
    source, the pins that fail on it; None when its run tells nothing. The original of every file is
    put back after each mutant."""
    matrix: dict[str, set[str] | None] = {}
    for key, (path, mutated) in sorted(mutants.items()):
        file = workdir / path
        original = file.read_text()
        try:
            file.write_text(mutated)
            matrix[key] = pins_failing(workdir, pins, run_tests, timeout)
        finally:
            file.write_text(original)
    return matrix
