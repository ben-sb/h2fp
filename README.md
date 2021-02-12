# http2 fingerprinter

A server to fingerprint http2 connections, implemented using a Python socket server.

## Usage

To run on localhost generate a self signed certificate for localhost and place the files in the certs directory (localhost.crt and localhost.key).
Make sure to trust the self signed certificate.

Run `python src/main.py` (or `python3 src/main.py` if on mac) and visit https://localhost:443 in your browser to see the fingerprint.
Ignore any certificate errors.