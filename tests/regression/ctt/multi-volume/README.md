# Multi-volume Dataset

Two volumes built from one feedstock.

This repository is a feedstock:
it holds the code that turns upstream data into books on the
[bookshelf](https://github.com/climate-resource/bookshelf).
Three things make up the dataset:

- `bookshelf.yaml` is the recipe, holding the metadata.
  `volume:` names the collection and its search vocabulary,
  `defaults:` holds what every version shares,
  and `books:` lists one entry per upstream version of the dataset.
- `build.py` is a Jupytext percent-format script holding only the processing.
  It calls `bookshelf.setup()` once, reads each declared input through `build.use(...)`,
  and writes its outputs with `build.book.write(..., used=[...])`.
- `inputs/` holds any input checked in alongside the code, rather than fetched from a URL.

## Getting started

Install the local virtual environment:

```bash
   make virtual-environment
```

Then build one version of the dataset:

```bash
   make run VERSION=v0.1.0
```

`VERSION` picks one entry from `books:` in the recipe.
The result lands in `bundle/v0.1.0`, validated, with no credentials needed and nothing uploaded.

## Changing the dataset

A new version of the dataset is a new entry under `books:`,
plus whatever `build.py` needs to process it.
`visibility:` sets who can see a book: `public`, `org` or `hidden`.
It applies to everything the build records,
and `visibility=` on a single `build.book.write(...)` call narrows one resource.

## Publishing

Publishing runs off pull requests, so there is nothing to run by hand and no credentials to set.
Opening a pull request builds a preview of every version the recipe declares,
and posts it as a comment that updates on each push.
Merging publishes that preview, and closing without merging discards it.

Everything else about this feedstock lives in the README of
[copier-bookshelf-dataset](https://github.com/climate-resource/copier-bookshelf-dataset):
setting the repository up, keeping it in step with the template,
and what CI does on a pull request.
