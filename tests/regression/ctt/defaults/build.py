# %% [markdown]
# # Example Dataset
#
# Test project made with copier-template-tester

# %% tags=["parameters"]
version = "v0.1.0"
input_sha256 = "sha256:9d4044e80da87a78fcd9153422b1f50ea527081f9f1a70a8d9e0248c77ff4e71"

# %%
import hashlib
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pandas as pd
from bookshelf import Bookshelf

# Stable identifiers keep identical builds byte deterministic.
resource_namespace = "https://github.com/climate-resource/ctt-project"
raw_tracking_id = uuid5(NAMESPACE_URL, f"{resource_namespace}/raw/{version}")
raw_activity_id = uuid5(NAMESPACE_URL, f"{resource_namespace}/fetch/{version}")
process_activity_id = uuid5(NAMESPACE_URL, f"{resource_namespace}/process/{version}")
output_tracking_id = uuid5(NAMESPACE_URL, f"{resource_namespace}/data/{version}")

# %% [markdown]
# # Fetch
#
# Replace this small cached example with a hash verified upstream input.

# %%
input_content = b"region,year,value\n" b"World,2020,1.0\n" b"World,2021,2.0\n"


class InputHashMismatchError(ValueError):
    """Raised when cached input bytes do not match their declared hash."""


def fetch_input(expected_sha256: str) -> Path:
    """Cache the example input and verify its declared content hash."""
    cache = Path(".cache") / "example.csv"
    cache.parent.mkdir(parents=True, exist_ok=True)
    if not cache.exists():
        cache.write_bytes(input_content)

    actual = f"sha256:{hashlib.sha256(cache.read_bytes()).hexdigest()}"
    if actual != expected_sha256:
        raise InputHashMismatchError
    return cache


raw_path = fetch_input(input_sha256)
raw_data = pd.read_csv(raw_path)

# %% [markdown]
# # Process

# %%
processed_data = raw_data.assign(value=raw_data["value"] * 2)


# %%
with Bookshelf() as client:
    with client.activity(
        kind="fetch",
        config={"version": version},
        activity_id=raw_activity_id,
    ) as activity:
        raw = activity.register(
            raw_data,
            type="tabular",
            logical_key=f"example/raw-{version}",
            tracking_id=raw_tracking_id,
        )

    with client.activity(
        kind="process",
        config={"version": version},
        activity_id=process_activity_id,
    ) as activity:
        data = activity.register(
            processed_data,
            type="timeseries",
            logical_key=f"example/data-{version}",
            used=[raw.tracking_id],
            tracking_id=output_tracking_id,
        )

    draft = client.draft_book(
        "example",
        version=version,
        license="MIT",
        visibility="public",
    )
    draft.attach(data, name_in_book="data")
    draft.publish()
