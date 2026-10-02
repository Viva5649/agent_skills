# Cache policy

`CacheController` applies a five-minute TTL to successful responses and exposes
the resulting expiry timestamp through its existing public response metadata.
