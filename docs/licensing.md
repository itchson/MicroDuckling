# License scope and publication boundaries

MicroDuckling's original source, documentation and independently generated mechanical designs use the [Apache License 2.0](../LICENSE). The adapted shadcn UI files listed in [third-party notices](../THIRD_PARTY_NOTICES.md) retain MIT notices. Installed dependencies keep their own licenses.

The public mechanical exports contain MicroDuckling's printed parts. Full local assemblies also use detailed Adafruit PCB-derived geometry and Pololu STEP models; those inputs and their exact derived meshes are omitted from the public repository. A different file format, raster render or aggregate scene does not automatically replace upstream rights.

Adafruit's hardware READMEs select [CC-BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) and request preserving their complete README text. The fetch script retrieves the original notices alongside both board files, including the additional MIT file in the LSM6DS3 repository. If redistributing board-derived representations, retain applicable attribution/licenses and explain extraction, estimated heights and placement changes. Do not claim all geometry is Apache-licensed. Whether a combined assembly is an adaptation or a collection depends on its construction; this repository avoids assuming a blanket share-alike scope for independent printed parts.

Pololu's models are manufacturer references. No general redistribution grant was established for these downloaded files, so they are fetched for local use instead of vendored. This is a publication boundary, not a claim that Pololu prohibits every form of incorporation.

Microduck is the inspiration, with credit to Pollen Robotics and Hugging Face. Its repositories provide Apache-licensed software, while Pollen's [press kit](https://pollen-robotics.com/microduck/press-kit/) limits the open-source statement to software. This repository distributes no official Microduck meshes, policies, product photography or branding. It is an independent hobby project with no upstream affiliation or endorsement.

Before publishing a changed build, use the public export/validation workflow, inspect the file list and retain the license scope. `build/local/` and `references/components_r02/` are intentionally ignored. Do not force-add full scenes, generated body-link meshes or a local archive to bypass that boundary.
