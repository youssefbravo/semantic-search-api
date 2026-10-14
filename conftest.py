import os
import sys

# Ensure the project root is importable so tests can `import app` / `import eval`
# regardless of pytest's working directory.
sys.path.insert(0, os.path.dirname(__file__))


def pytest_addoption(parser):
    parser.addoption("--strict-integration", action="store_true", help="Fail if any test is skipped")


def pytest_sessionfinish(session, exitstatus):
    if session.config.getoption("--strict-integration"):
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if reporter and reporter.stats.get("skipped"):
            reporter.write_sep("=", "Strict verification failed: skipped tests are not passes")
            session.exitstatus = 1
