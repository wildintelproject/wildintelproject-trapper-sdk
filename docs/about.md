# About

## wildintel-trapper-sdk and WildINTEL

**wildintel-trapper-sdk** is a typed Python client for the REST API of
[Trapper](https://gitlab.com/trapper-project/trapper), the open-source platform used to manage and
classify camera-trap data: locations, deployments, media resources, storage collections, research
projects, and both manual and AI-assisted classification results.

It exists to give the other tools in the [WildINTEL](https://wildintel.eu/) toolchain — such as
[wildintel-publisher](https://github.com/wildintelproject/wildintel-publisher), which fetches
Camtrap DP packages from a Trapper classification project for publication to open-data repositories
— a single, typed, well-tested way to talk to a Trapper server, instead of every tool re-implementing
its own HTTP calls and pagination handling.

The library covers Trapper's read-only REST API in full, and adds write access for the two resources
the API doesn't expose (locations and deployments) by simulating the classic web UI's import forms —
a documented workaround, not a stable API contract, kept clearly separated from the rest of the
client's interface.

---

## Funding

This work is part of the [WildINTEL project](https://wildintel.eu/), funded by the
[Biodiversa+](https://www.biodiversa.eu/) Joint Research Call 2022–2023 *"Improved transnational
monitoring of biodiversity and ecosystem change for science and society (BiodivMon)"*.

Biodiversa+ is the European co-funded biodiversity partnership supporting excellent research on
biodiversity with an impact for policy and society. Biodiversa+ is part of the European Biodiversity
Strategy for 2030 that aims to put Europe's biodiversity on a path to recovery by 2030 and is
co-funded by the European Commission.

---

## License

This project is licensed under the [GNU General Public License v3.0 or later](https://www.gnu.org/licenses/gpl-3.0.html).
