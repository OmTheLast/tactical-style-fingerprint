import json
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import urlopen

import certifi


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MATCHES_PATH = PROJECT_ROOT / "data/raw/statsbomb/matches/2-27.json"
EVENTS_DIR = PROJECT_ROOT / "data/raw/statsbomb/events"
EVENT_URL = "https://raw.githubusercontent.com/hudl/open-data/master/data/events/{match_id}.json"
MAX_WORKERS = 8
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def download_match(match_id: int) -> str:
    destination = EVENTS_DIR / f"{match_id}.json"
    if destination.exists():
        try:
            cached_events = json.loads(destination.read_text())
            if isinstance(cached_events, list):
                return "cached"
        except (json.JSONDecodeError, OSError):
            pass

    with urlopen(
        EVENT_URL.format(match_id=match_id),
        timeout=60,
        context=SSL_CONTEXT,
    ) as response:
        payload = response.read()

    events = json.loads(payload)
    if not isinstance(events, list):
        raise ValueError(f"Expected a JSON list for match {match_id}")

    temporary = destination.with_suffix(".json.tmp")
    temporary.write_bytes(payload)
    temporary.replace(destination)
    return "downloaded"


def main() -> None:
    matches = json.loads(MATCHES_PATH.read_text())
    match_ids = [match["match_id"] for match in matches]
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)

    counts = {"cached": 0, "downloaded": 0}
    failures = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(download_match, match_id): match_id
            for match_id in match_ids
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            match_id = futures[future]
            try:
                counts[future.result()] += 1
            except Exception as error:
                failures.append((match_id, str(error)))

            if completed % 25 == 0 or completed == len(futures):
                print(f"Checked {completed}/{len(futures)} match files")

    print(f"Cached: {counts['cached']}; downloaded: {counts['downloaded']}")
    if failures:
        details = "\n".join(f"{match_id}: {error}" for match_id, error in failures)
        raise RuntimeError(f"Failed to download {len(failures)} matches:\n{details}")


if __name__ == "__main__":
    main()
