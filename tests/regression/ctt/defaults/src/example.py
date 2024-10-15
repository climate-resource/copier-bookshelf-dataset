# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -pycharm
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.14.0
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
import logging
import tempfile

from bookshelf import LocalBook
from bookshelf_producer.notebook import load_nb_metadata
from scmdata.testing import get_single_ts

# %% [markdown]
# #  Initialise

# %%
logging.basicConfig(level="INFO")

# %%
metadata = load_nb_metadata("example")
metadata.dict()

# %% tags=["parameters"]
local_bookshelf = tempfile.mkdtemp()

# %%
local_bookshelf

# %%
book = LocalBook.create_from_metadata(
    metadata,
    local_bookshelf=local_bookshelf,
)

# %% [markdown]
# #  Fetch data

# %%
# local_fname = metadata.download_file()
# emissions = scmdata.ScmRun(local_fname, lowercase_cols=True)
# emissions

# %% [markdown]
# # Process

# %%
book.add_timeseries("example", get_single_ts())

# %%
book.metadata()
