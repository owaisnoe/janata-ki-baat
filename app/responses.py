"""Serve in-memory bytes without tripping the WSGI file-wrapper.

LiteSpeed/Passenger's wsgi.file_wrapper calls .fileno() on whatever
send_file() streams. A real file has one; an in-memory BytesIO/StringIO does
not, so send_file(BytesIO(...)) raises io.UnsupportedOperation: fileno under
Passenger (but not under Flask's test client, which skips the wrapper).
Generated artifacts (PDFs, QR PNGs, CSVs) are built in memory, so they must
be returned as a plain Response with the bytes already read out. Disk-backed
files keep using send_file — they have a real fileno.
"""
from flask import Response


def send_inline_bytes(buf, mimetype, download_name=None, as_attachment=False):
    data = buf.getvalue() if hasattr(buf, "getvalue") else buf.read()
    if isinstance(data, str):
        data = data.encode("utf-8")
    headers = {}
    if download_name:
        disp = "attachment" if as_attachment else "inline"
        headers["Content-Disposition"] = f'{disp}; filename="{download_name}"'
    return Response(data, mimetype=mimetype, headers=headers)
