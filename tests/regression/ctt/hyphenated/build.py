# %% [markdown]
# # PRIMAP-hist 2024
#
# Historical national emissions, hyphenated and numbered.
#
# The recipe in `bookshelf.yaml` names the version, the licence, the discovery metadata
# and the inputs.
#
# This file contains the code that processes the data into a form used by the bookshelf.

# %%
import bookshelf
import pandas as pd

# %%
build = bookshelf.setup()

# %% [markdown]
# # Fetch
#
# `build.use` resolves a resource named in the recipe,
# and registers them as an input of this build.
# The recipe states the authorship of `raw`, so nothing about it is repeated here.

# %%
raw = build.use("raw")
raw_data = pd.read_csv(raw.path)
raw_data.head()

# %% [markdown]
# # Process
#
# TODO: Replace this with the real transform.

# %%
# A timeseries is stored wide, one column per year, so the long input is pivoted.
processed_data = (
    raw_data.assign(value=raw_data["value"] * 2)
    .pivot(index=["region", "dataset"], columns="year", values="value")
    .reset_index()
)
processed_data.columns = [str(column) for column in processed_data.columns]

# %% [markdown]
# # Publish
#
# The recipe never names what a build writes,
# so an output states its own catalogue metadata here, credited to whoever derived it.

# %%
build.book.write(
    "data",
    processed_data,
    type="timeseries",
    used=[raw],
    description="The processed output this build derives from `raw`.",
    authors=[
        {
            "name": "Ada Lovelace",
            "email": "ada.lovelace@climate-resource.com",
        }
    ],
)
build.book.publish()
