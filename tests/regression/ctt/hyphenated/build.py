# %% [markdown]
# # PRIMAP-hist 2024
#
# Historical national emissions, hyphenated and numbered.

# %% tags=["parameters"]
version = "v0.1.0"
input_sha256 = "sha256:e34c37970248b64af3b9bccc471fe9bb6b8780c434a20166ca086988c6b2e9b3"

# %%
import hashlib
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import bookshelf
import pandas as pd

# Stable identifiers keep identical builds byte deterministic.
resource_namespace = "https://github.com/climate-resource/bookshelf-primap-hist-2024"
raw_tracking_id = uuid5(NAMESPACE_URL, f"{resource_namespace}/raw/{version}")
output_tracking_id = uuid5(NAMESPACE_URL, f"{resource_namespace}/data/{version}")
build_activity_id = uuid5(NAMESPACE_URL, f"{resource_namespace}/build/{version}")

# %% [markdown]
# # Fetch
#
# Replace this small cached example with a hash verified upstream input.
# %%
# The dataset column keeps this example distinct from every other generated feedstock.
# Registration deduplicates on content, so identical example bytes would alias
# onto whichever feedstock published them first and could not then be attached.
input_content = (
    b"region,dataset,year,value\n"
    b"World,primap-hist-2024,2020,1.0\n"
    b"World,primap-hist-2024,2021,2.0\n"
    b"World,primap-hist-2024,2022,3.0\n"
)


class InputHashMismatchError(ValueError):
    """Raised when cached input bytes do not match their declared hash."""

    def __init__(self, path: Path, actual: str, expected: str) -> None:
        super().__init__(
            f"{path} hashes to {actual}, but this build declares {expected}. "
            "Update input_sha256 to accept the new bytes, "
            "or delete the cached file to fetch the input again."
        )


def fetch_input(expected_sha256: str) -> Path:
    """Cache the example input and verify its declared content hash."""
    cache = Path(".cache") / "primap-hist-2024.csv"
    cache.parent.mkdir(parents=True, exist_ok=True)
    if not cache.exists():
        cache.write_bytes(input_content)

    actual = f"sha256:{hashlib.sha256(cache.read_bytes()).hexdigest()}"
    if actual != expected_sha256:
        raise InputHashMismatchError(cache, actual, expected_sha256)
    return cache


raw_path = fetch_input(input_sha256)
raw_data = pd.read_csv(raw_path)

# %% [markdown]
# # Process

# %%
processed_data = raw_data.assign(value=raw_data["value"] * 2)

# %%
# The collection, licence, visibility and authors come from bookshelf.yaml.
# This file is executed by the recorder, so it does not construct a client itself.
client, draft = bookshelf.setup(version=version)

# A recorded build carries exactly one activity block.
with client.activity(
    kind="build",
    config={"version": version},
    activity_id=build_activity_id,
) as activity:
    raw = activity.register(
        raw_data,
        type="tabular",
        logical_key=f"primap-hist-2024/raw-{version}",
        tracking_id=raw_tracking_id,
    )
    data = activity.register(
        processed_data,
        type="timeseries",
        logical_key=f"primap-hist-2024/data-{version}",
        used=[raw.tracking_id],
        tracking_id=output_tracking_id,
    )

draft.attach(data, name_in_book="data")
draft.publish()
