# Build the report with a vendored IEEEtran and a manual bibliography

The report must fit six pages and use the IEEE conference look without a
fragile external bibliography pipeline. We vendor `IEEEtran.cls`, keep the
references in a manual `thebibliography` list, and compile with Tectonic 0.17.0
to validate layout and page count. The PDF is committed alongside the sources.

**Consequences**: the build is self-contained apart from the TeX distribution.
Tectonic downloads its bundle on first use. Page-count changes still require a
manual check because floating figures and tables can move; the current build is
six pages with references and CRediT on page 6.
