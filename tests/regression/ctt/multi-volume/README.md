# Multi-volume Dataset

Two volumes built from one feedstock.

This repository contains the code to generate the Multi-volume Dataset book
for the [bookshelf](https://github.com/climate-resource/bookshelf).

## Getting started

Install the local virtual environment:

```bash
   make virtual-environment
```

A bundle holds one book, so a version selects both what is recorded and where it lands:

```bash
   make run VERSION=v0.1.0
```

That records and validates `bundle/v0.1.0` without any API credentials.

A first publish into a new volume needs that volume to exist.
`bookshelf publish` will not create one, so it fails with `Series 'multi-volume' not found`.
Create it once, from an account with WRITE:

```bash
   uv run bookshelf volume create multi-volume --licence CC-BY-4.0
```

## Changing the dataset

The dataset is two files:

- `bookshelf.yaml` is the recipe for the metadata about the dataset.
  `volume:` names the collection and its search vocabulary,
  `defaults:` holds what every book shares,
  and `books:` lists one entry per upstream version of the dataset.
- `build.py` holds only the processing.
  It calls `bookshelf.setup()` once, reads each declared input through `build.use(...)`,
  and writes its outputs with `build.book.write(..., used=[...])`.

Everything else about this feedstock lives in the README of
[copier-bookshelf-dataset](https://github.com/climate-resource/copier-bookshelf-dataset):
setting the repository up, keeping it in step with the template,
and how a pull request is previewed and published.
