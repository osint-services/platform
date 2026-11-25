# Certificate inventory evidence contract

Inventory accepts observations for DNS domains configured by the operator after verifying ownership. A certificate name alone cannot add a domain to scope or establish that a host is live.

Compare lowercase ASCII DNS names in A-label form after removing one trailing root dot. Reject malformed names, IP literals, empty labels and embedded wildcards. For an initial implementation, reject Unicode input until converted to a valid A-label. A name is in scope when its base equals the configured domain or ends in a dot followed by that domain. For matching only, strip one leading `*.`. Preserve the wildcard in the stored name and never expand it into inferred hosts.

Each observation records the configured domain, normalized certificate name, source identifier, source-specific certificate ID, certificate validity start and end, log timestamp and retrieval timestamp. Use UTC RFC 3339 timestamps. Retrieval time is required. Preserve missing upstream timestamps as null. A validity boundary is never a substitute for log time. Deduplicate by configured domain, source, certificate ID and normalized name.

A completed empty lookup, provider failure and invalid response are distinct outcomes. On failure retain the last successful snapshot and expose its age. Treat an absent name as absent from that snapshot only.

See [synthetic acceptance cases](../examples/certificate-inventory/contract.json). Each case overrides the example observation's name and states the expected scope decision.
