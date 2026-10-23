# R17.7 R03 readback check R01

[Company-laptop steps](OPEN%20FIRST%20-%20READBACK.txt).

The operator's R03 output reports all 72 numeric comparisons matched, including
54 direct baseline values and 18 definition-checked variance expectations versus
72 actual candidate values. The private backup was verified and an update was
submitted. Readback then reported three added properties, seventeen identical
measure DAX line representations and two identical calculated-helper line
representations. CloudConnectionPreserved was true. No refresh was requested.

The output's public SHA-256 path tokens resolve to isNameInferred on the new
ImportedAtUTC/FileChoiceLabel columns of fm_native_files and SeriesLabel of
fm_native_lines. The property values remain unknown from that output. Microsoft
defines [IsNameInferred](https://learn.microsoft.com/en-us/dotnet/api/microsoft.analysisservices.tabular.calculatedtablecolumn?view=analysisservices-dotnet)
as calculated-column naming metadata. Its [protocol definition](https://learn.microsoft.com/en-us/openspecs/sql_server_protocols/ms-ssas-t/ae53bf0d-ebc9-4760-8267-08c2fa8c481f)
distinguishes server-inferred true from explicitly specified false. Do not
assume a value or globally ignore the property.

The standalone check is read only. It pins the exact reported R03 backup folder,
reads each of four files twice to temporary local files, verifies stable full
UTF-8 bytes/length, and parses without duplicate JSON keys. Public-code hashes
independently verify the R17.6 input and R17.7 candidate. Reversing only declared
measure/helper/column additions must reproduce the complete saved before
definition; extra source/security/part/format/connection changes are rejected.
The saved preflight receipt must match the reported successful R03 evidence.
No company amount query is repeated.

The API wrapper admits only exact TEST identity/connections/getDefinition and
their read-only operation-status routes. Two complete metadata and connection
snapshots must be stable and match the private candidate and saved mapping.
Only the three exact new columns can admit an added boolean isNameInferred=true,
and only with calculatedTableColumn type and the exact [ColumnName] source
binding. After removing those flags from an in-memory comparison copy, the
whole definition must match, except already-supported identical DAX string/line
representations. False/nonboolean values, flags elsewhere and any other
metadata change remain unexplained. This is not a blanket metadata ignore.
Output contains only safe paths, booleans, counts and the compact preflight
receipt; no model/source/connection contents or raw differing values.

TEST_R177_READBACK_VERIFIED permits the single existing-TEST metadata refresh,
then the unchanged R17.7 TEST PBIP only after warning-free Completed. All other
stages stop for review. No updater retry, rollback, refresh API or publish is
performed by this check. Production R16.6 and older artifacts remain untouched.
The check establishes configuration readback, not post-refresh numerical/UI
parity or speed. The reported original 74710ms and candidate 99848ms preflight
totals have different direct query counts (54 versus 72) and are not report
performance evidence.

Local synthetic guards reproduce the reported 3+17+2 differences and exercise
unknown flags, wrong bindings, source/security/formula/format/order changes,
tampered backups/receipts, truncated/changing UTF-8 reads, unstable snapshots,
wrong identity and forbidden mutation routes. Python 3.10 syntax parses. These
are not live company checks. GitNexus cannot resolve Coordination; direct
source/hash tracing, guards and prior-file preservation are bounded fallback.
