## MODIFIED Requirements

### Requirement: Evidence reachability is explicit

Repository evidence SHALL distinguish immutable run identity from mutable scope-local current heads, named release pins, and active execution leases. A run is current or retained only through exact validated bindings; directory names and modification times MUST NOT provide authority. Currentness lookup SHALL use one indexed observation per invocation rather than scanning the complete receipt store separately for each owner.

#### Scenario: Current head references a changed result

- **WHEN** the result fingerprint no longer matches the current-head binding
- **THEN** the head is invalid and the run cannot support a current claim

#### Scenario: Unreachable run is classified

- **WHEN** a run has no current-head, pin, or active-lease reference
- **THEN** the lifecycle index SHALL classify it as collectible and SHALL not treat it as current

#### Scenario: One invocation has many owners

- **WHEN** multiple owners request receipt currentness in one frozen invocation
- **THEN** they SHALL project from one receipt index and SHALL not each rescan the store
