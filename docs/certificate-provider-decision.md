# Certificate inventory provider decision

Select a direct crt.sh JSON adapter for the initial inventory of configured organization-owned domains. Both candidates depend on the same upstream service. Neither provides independent corroboration of domain ownership.

| Criterion | Direct JSON adapter design | Metabigor certificate command at 5785d654 |
| --- | --- | --- |
| Transport | Require normal TLS certificate and hostname verification. Treat TLS failures as failed attempts. | The command uses the shared HTTP client, which disables TLS verification. |
| Empty and failed lookups | Accept an empty snapshot only after a successful HTTP response containing a valid JSON array. Reject invalid rows atomically. Timeouts and upstream errors preserve the last snapshot. | HTTP and parse errors are logged at debug level and return no entries. The command can exit successfully with no output. |
| Evidence | Preserve per-certificate ID, name, validity dates and available log timestamp. Record retrieval and snapshot completion separately. | The CLI groups by domain. Its first-seen field uses the earliest validity start. |

The [offline experiment](../tests/test_certificate_provider_evaluation.py) translates the three [contract scenarios](../examples/certificate-inventory/contract.json) into synthetic provider rows and a simulated timeout. It uses fixture expectations for hostname scope so it evaluates response handling only. All scenarios pass. Source inspection shows that the Metabigor CLI cannot reliably distinguish the empty-success and timeout cases from its exit status and records alone. We did not run it against a live domain.

Before release, verify the actual provider schema, timestamp formats, truncation behavior and TLS failure handling in the implemented adapter. The offline experiment does not establish uptime, completeness or live compatibility.

Sources: [certificate command](https://github.com/j3ssie/metabigor/blob/5785d654207340b795b6af06e0f45230a6db073c/internal/cli/cert.go), [HTML parser](https://github.com/j3ssie/metabigor/blob/5785d654207340b795b6af06e0f45230a6db073c/internal/cert/crt.go), [HTTP client](https://github.com/j3ssie/metabigor/blob/5785d654207340b795b6af06e0f45230a6db073c/internal/httpclient/client.go).
