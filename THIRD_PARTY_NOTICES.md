# Third-party notices

DocFlow source and its synthetic corpus/fixtures are supplied under the repository's
MIT license. The multinomial Naive Bayes implementation reuses the previous starter's
MIT-licensed local classifier. No external model weights, real documents or customer
data are bundled.

Runtime dependencies: FastAPI (MIT), Starlette (BSD-3-Clause), Pydantic and pydantic-core
(MIT), Uvicorn (BSD-3-Clause), pypdf (BSD-3-Clause), plus their transitive dependencies.
The OpenAI Python SDK (Apache-2.0) supplies the Azure client; python-dotenv uses
BSD-3-Clause. The frontend uses React/React DOM and Vite (MIT).
Development tools include pytest (MIT), HTTPX (BSD-3-Clause), and Pillow (MIT-CMU).
The lock records exact packages and published wheel hashes; installed distributions
contain their authoritative license texts. Pillow generates the optional synthetic PNG.

Tesseract OCR is optional system software, separately installed, licensed under
Apache-2.0; its Leptonica dependency uses a BSD-style license. No OCR executable or
language data is distributed by this repository. Obtain those from the official
Tesseract project or your operating system's package source before the timed event.

NetGreener is a separate proprietary product participants discover and install
independently. Its SDK, implementation, credentials and integration code are not
included in the clean participant starter.
