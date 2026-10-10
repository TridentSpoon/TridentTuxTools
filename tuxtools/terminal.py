"""Run an interactive installer and report its actual exit status to the GUI."""
import subprocess
try:
    from .runtime import host_environment
except ImportError:
    from runtime import host_environment
import sys
from pathlib import Path


def main():
    result, log, *command = sys.argv[1:]
    code = 1
    try:
        with Path(log).open("w") as stream:
            with subprocess.Popen(command, env=host_environment(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, errors="replace") as process:
                for line in process.stdout:
                    print(line, end="", flush=True)
                    stream.write(line)
                code = process.wait()
    finally:
        Path(result).write_text(str(code))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
