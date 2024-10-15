# {{dataset_name_human}}

{{dataset_name_description}}

This repository contains the code to generate the {{dataset_name_human}} book for the [bookshelf](https://github.com/climate-resource/bookshelf).

## Getting started

Install the local virtual environment:

```bash
   make virtual-environment
```

The configuration that describes the book is in `src/{{dataset_name}}.yaml`
while the source code to process the book is in `src/{{dataset_name}}.py`.


The book can be generated using `make run`,
which produces some outputs which are stored in `dist/`.
This includes the generated CSV files and the rendered notebook
that was used to generate the book.

These build artifacts can then be published to the bookshelf using `make publish`
(not currently working).
Generally this is done automatically by the CI/CD pipeline on a new release.
