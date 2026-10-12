"""Run an interactive installer and report its actual exit status to the GUI."""
import subprocess
import codecs
import os
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
        with Path(log).open("w") as stream, open("/dev/tty", "r") as keyboard:
            with subprocess.Popen(command, env=host_environment(), stdin=keyboard, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  ) as process:
                decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
                while True:
                    chunk = os.read(process.stdout.fileno(), 4096)
                    if not chunk:
                        break
                    text = decoder.decode(chunk)
                    print(text, end="", flush=True)
                    stream.write(text)
                    stream.flush()
                tail = decoder.decode(b"", final=True)
                print(tail, end="", flush=True)
                stream.write(tail)
                code = process.wait()
    finally:
        Path(result).write_text(str(code))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
