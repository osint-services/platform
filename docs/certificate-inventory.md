# Certificate inventory evidence contract

Inventory accepts observations for DNS domains configured by the operator after verifying ownership. A certificate name alone cannot add a domain to scope or establish that a host is live.

Compare lowercase ASCII DNS names in A-label form after removing one trailing root dot. Reject malformed names, IP literals, empty labels and embedded wildcards. For an initial implementation, reject Unicode input until converted to a valid A-label. A name is in scope when its base equals the configured domain or ends in a dot followed by that domain. For matching only, strip one leading `*.`. Preserve the wildcard in the stored name and never expand it into inferred hosts.

Each observation records the configured domain, normalized certificate name, source identifier, source-specific certificate ID, certificate validity start and end, log timestamp and retrieval timestamp. Use UTC RFC 3339 timestamps. Retrieval time is required. Preserve missing upstream timestamps as null. A validity boundary is never a substitute for log time. Deduplicate by configured domain, source, certificate ID and normalized name.

## Refresh outcomes

Validate the complete provider response before publishing. Skip an individual malformed or out-of-scope name in an otherwise valid certificate record and continue processing its other names. A successful response with zero accepted names publishes an empty snapshot. An unreadable payload, unexpected response structure, or certificate record missing its required identifier invalidates the whole refresh, even if earlier records were valid. A timeout or upstream outage is a provider failure.

Publish each successful snapshot atomically for its configured domain and source. Store a snapshot-level UTC RFC 3339 `completed_at` even when the observations list is empty. On provider failure or invalid response, record the attempt outcome separately and retain the previous successful snapshot, including its completion time. Compute its age from that time. If no successful snapshot exists, report its age as unavailable.

The [synthetic fixtures](../examples/certificate-inventory/contract.json) include individual name cases and ordered refresh scenarios. In each scenario, certificate IDs and timestamps other than snapshot completion inherit the example observation unless overridden. Expected snapshots list normalized names for brevity.

## Using the inventory

Set `CERTIFICATE_INVENTORY_DOMAINS` to a comma-separated list of domains whose ownership you have verified, then recreate the dataset service. The default list is empty. List configured domains with GET `/datasets/certificate-inventory`. POST `/datasets/certificate-inventory/{domain}/refresh` to request certificate observations and GET `/datasets/certificate-inventory/{domain}` to read the stored result. Use the canonical domain returned by the list endpoint. Refresh responses include `last_outcome`; clients should show stale results with their age after a failed attempt. Results reflect records returned by crt.sh. Coverage is not guaranteed. The default single-worker service serializes refreshes per domain and uses the existing persistent dataset volume.
