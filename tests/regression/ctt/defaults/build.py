# %% [markdown]
# # Example Dataset
#
# Test project made with copier-template-tester

# %% tags=["parameters"]
version = "v0.1.0"

# %%
import asyncio
from uuid import NAMESPACE_URL, uuid5

import bookshelf_client as bookshelf
import pandas as pd

# %%
recorder, book = bookshelf.setup(version=version, visibility="public")

# Stable identifiers keep identical builds byte deterministic.
resource_namespace = "https://github.com/climate-resource/ctt-project"
raw_tracking_id = uuid5(NAMESPACE_URL, f"{resource_namespace}/raw/{version}")
activity_id = uuid5(NAMESPACE_URL, f"{resource_namespace}/process/{version}")
output_tracking_id = uuid5(NAMESPACE_URL, f"{resource_namespace}/data/{version}")

# %% [markdown]
# # Fetch
#
# Replace this small example with a hash verified upstream input.

# %%
raw_data = pd.DataFrame(
    {
        "region": ["World", "World"],
        "year": [2020, 2021],
        "value": [1.0, 2.0],
    }
)

# %% [markdown]
# # Process

# %%
processed_data = raw_data.assign(value=raw_data["value"] * 2)


# %%
async def main() -> None:
    """Register inputs and outputs with explicit lineage, then publish."""
    raw = await recorder.register(
        raw_data,
        type="tabular",
        logical_key=f"example/raw-{version}",
        tracking_id=raw_tracking_id,
    )

    async with recorder.activity(
        kind="process",
        parameters={"version": version},
        activity_id=activity_id,
    ) as activity:
        data = await activity.register(
            processed_data,
            type="timeseries",
            logical_key=f"example/data-{version}",
            used=[raw.tracking_id],
            tracking_id=output_tracking_id,
        )

    book.attach(data, "data")
    book.publish()


asyncio.run(main())
