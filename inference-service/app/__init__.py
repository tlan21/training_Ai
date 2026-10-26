import sys

# Windows gives redirected stdout/stderr the ANSI code page (cp1252): a Vietnamese log line raised
# UnicodeEncodeError inside a handler and turned 503 envelopes into 500 plain text (AI-06/AI-07).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="backslashreplace")
