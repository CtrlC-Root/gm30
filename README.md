# Radioddity GM30

This repository contains reverse engineered programming protocol documentation and a reference implementation.

## Development

Create a Python virtual environment:

```bash
python -m venv env
source env/bin/activate
```

Install the Python package in editable mode:

```bash
pip install -e .
```

Connect your radio to the computer with the USB programming cable, turn it on,
and wait for it to boot. Run the client with `--help` to see usage help:

```bash
gm30 --help
```

Run the `test_read.sh` script to read the connected radio's active
configuration:

```bash
./test_read.sh
```
