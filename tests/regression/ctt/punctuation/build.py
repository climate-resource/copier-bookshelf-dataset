# %% [markdown]
# # NGFS "Net Zero" Scenarios
#
# Scenario data for O'Brien's review: quoted, apostrophised and colonised.
#
# The recipe in `bookshelf.yaml` names the version, the licence, the discovery metadata
# and the inputs, so this file holds only the processing.

# %%
import bookshelf
import pandas as pd

# %%
build = bookshelf.setup()

# %% [markdown]
# # Fetch
#
# `build.use` resolves the name the recipe declares, hashes the bytes and registers
# them as an input of this build.

# %%
raw = build.use("raw")
raw_data = pd.read_csv(raw.path)
raw_data.head()

# %% [markdown]
# # Process
#
# Replace this with the real transform.

# %%
processed_data = raw_data.assign(value=raw_data["value"] * 2)

# %% [markdown]
# # Publish
#
# `used=[raw]` is what records the lineage edge from the input to this output.

# %%
build.book.write("data", processed_data, type="timeseries", used=[raw])
build.book.publish()
