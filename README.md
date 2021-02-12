# http2 fingerprinter

A server to fingerprint http2 connections, implemented using a Python socket server.

## Usage

To run on localhost generate a self signed certificate for localhost and place the files in the certs directory (localhost.crt and localhost.key).
Make sure to trust the self signed certificate.

Run `python src/main.py` (or `python3 src/main.py` if on mac) and visit https://localhost:443 in your browser to see the fingerprint.
Ignore any certificate errors.

## For anyone interested

This works by having a socket pretend to be a real http2 server, communication is only implemented as far as needed to determine the fingerprint. Although not a full http2 implementation (as there is no state machine), it could technically be extended to that.<br/>
If you are interested in more than just the standard fingerprint you can view all of the frames sent by the browser in the process method in the src/connection.py file.