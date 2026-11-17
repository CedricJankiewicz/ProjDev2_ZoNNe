import csv

FIELDS = ["x", "y", "label"]


def write_csv(path, rows):
    """Write a list of (x, y, label) tuples to a CSV file."""
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)
        writer.writerows(rows)


def read_csv(path, valid_labels):
    """Read a CSV file and return a list of (x, y, label) integers.

    Raises FileNotFoundError if the file does not exist and
    ValueError if its content is corrupted.
    """
    try:
        with open(path, newline="") as f:
            rows = [(int(r["x"]), int(r["y"]), int(r["label"]))
                    for r in csv.DictReader(f)]
    except (KeyError, TypeError):   # missing column or short line
        raise ValueError("malformed file")
    if any(label not in valid_labels for _, _, label in rows):
        raise ValueError("invalid label")
    return rows