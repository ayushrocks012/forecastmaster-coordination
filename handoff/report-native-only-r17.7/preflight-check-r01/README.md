# R17.7 read-only preflight diagnostic R01

[Company-laptop instructions](OPEN%20FIRST%20-%20PREFLIGHT%20CHECK.txt).

The receiving run on 23 October 2026 discovered an ADS scope, then failed in
`original = query(build_query(scopes[0], {}))` with `FabricAdomdException`.
The existing updater suppresses the actual message. The failure preceded the
candidate query, all R17.7 backups and `updateDefinition`. This run made no
model write; the exception type alone does not identify its cause.

First inspect a matching earlier preflight exception retained by IPython in
`sys.last_value`/`sys.last_exc`. Python retains `__context__` even though the
updater's `raise ... from None` suppresses it in the printed traceback. If its
underlying category is recognized, return `R177_PREFLIGHT_PREVIOUS_ERROR_CAPTURED`
without any new DAX reads. This depends on the notebook session retaining that
exception; it is not guaranteed after a session restart or subsequent error.
Unrelated exceptions are ignored. Only the safe classification is printed.

The frozen updater requests 18 rows with four values each in one UNION query.
This diagnostic uses the same metadata scope discovery and filters, but reads
four individual baseline scalars in sequence: Market/12M current-year FY Plan,
Benchmark and Variance %, then December of the next year for Trend Monthly.
It stops at the first query failure. The smaller scope reduces combined work;
it does not guarantee a lower peak, diagnose the original failure by itself,
prove full coverage, or replace the 72 old/candidate comparisons.

Only the fixed existing TEST UUID is evaluated with
`use_readwrite_connection=False`. There is no REST client, filesystem writer,
candidate DEFINE MEASURE, processing, source ingestion, refresh or publish.
Company values and raw exception messages are inspected in notebook memory.
Output contains fixed labels, elapsed durations, BLANK/NUMERIC state and only
allowlisted error categories/codes/query positions/memory limits. An unknown
error remains UNCLASSIFIED. No query text, scope values or raw errors are sent
to this public repository. No error classification is a numerical parity pass.

`R177_SMALL_BASELINE_READS_COMPLETED` means only the four small reads returned
the expected shape; BLANK is reported honestly. Send every final JSON result
back for review. Neither that stage nor a failure permits rerunning the frozen
updater or refreshing/opening R17.7 as installed. No production change.

Local mocks test previous-error recovery, query scope, read-only routing, fail-fast behavior, privacy,
blank/zero distinction, exception wrappers and Python 3.10 syntax. They do not
execute DAX or prove company runtime performance. GitNexus cannot resolve this
repository; direct call-site tracing and preservation tests are bounded
fallback evidence, not a complete graph impact result.

Microsoft references:

- [SemPy evaluate_dax](https://learn.microsoft.com/en-us/python/api/semantic-link-sempy/sempy.fabric?view=semantic-link-python): read-only connection parameter.
- [Query memory and timeout limits](https://learn.microsoft.com/en-us/fabric/enterprise/powerbi/service-admin-premium-workloads): limits can affect XMLA queries; the current exception does not yet establish either condition.
