import argparse
import hashlib
import json
from pathlib import Path
import shutil


def file_md5(path: Path) -> str:
    hash_md5 = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Excel file into raw zone")
    parser.add_argument("--source", required=True, help="Path to source .xlsx")
    parser.add_argument("--dest", required=True, help="Path to destination .xlsx")
    parser.add_argument("--state-file", required=True, help="Path to ingest state json")
    args = parser.parse_args()

    source = Path(args.source)
    dest = Path(args.dest)
    state_file = Path(args.state_file)

    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    state_file.parent.mkdir(parents=True, exist_ok=True)

    checksum = file_md5(source)
    shutil.copy2(source, dest)

    state = {
        "source": str(source),
        "destination": str(dest),
        "md5": checksum,
    }
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"Ingested file to {dest}")
    print(f"Source checksum: {checksum}")


if __name__ == "__main__":
    main()
