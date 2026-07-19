## ADDED Requirements

### Requirement: Configure one AutoDL connection
The platform SHALL allow the user to configure exactly one active AutoDL connection using host, port, username, private-key reference, remote experiment root, and ComfyUI path settings, and SHALL keep the private key material local.

#### Scenario: Save a connection configuration
- **WHEN** the user provides valid connection settings and saves them
- **THEN** the platform stores the non-secret settings locally and stores only a local reference to the private key

#### Scenario: Detect an unavailable instance
- **WHEN** the user tests the connection while AutoDL is stopped or unreachable
- **THEN** the platform reports a diagnosable connection failure and does not create a false healthy state

### Requirement: Test the AutoDL connection
The platform SHALL provide a connection test that verifies SSH access, the configured remote experiment root, and access to the configured ComfyUI workspace.

#### Scenario: Connection test succeeds
- **WHEN** AutoDL is running and the configured SSH key and paths are valid
- **THEN** the platform reports success and shows the resolved remote paths

#### Scenario: Connection test identifies a path problem
- **WHEN** SSH succeeds but a configured remote path is missing or inaccessible
- **THEN** the platform reports SSH success separately from the path failure and identifies the failing path

### Requirement: Synchronize an experiment on demand
The platform SHALL let the user manually synchronize one experiment's remote workspace over SSH/SFTP and SHALL transfer only files that match the experiment artifact allowlist or have been explicitly marked for inclusion.

#### Scenario: Download selected artifacts
- **WHEN** the user clicks synchronize for an experiment with a reachable remote workspace
- **THEN** the platform downloads new or changed original images, masks, saved images, workflow JSON files, and supported metadata into the local experiment directory

#### Scenario: Ignore unrelated files
- **WHEN** the remote workspace contains temporary previews, caches, or files outside the allowlist
- **THEN** the platform leaves those files out of the local snapshot and reports the ignored-file count

#### Scenario: Retry an interrupted transfer
- **WHEN** a file transfer fails or a file is still changing during synchronization
- **THEN** the platform records the failure or pending state, keeps completed transfers, and allows the user to retry without corrupting earlier snapshots

### Requirement: Record synchronization snapshots
Each synchronization SHALL produce a snapshot record containing sync time, source path, transferred artifacts, checksums or equivalent change identifiers, and per-file transfer status.

#### Scenario: Successful snapshot
- **WHEN** synchronization completes with all selected files transferred
- **THEN** the platform marks the snapshot successful and makes its artifacts available for comparison and evaluation

#### Scenario: Partial snapshot
- **WHEN** some selected files transfer successfully and others fail
- **THEN** the platform marks the snapshot partial, shows the failed files, and preserves the successful files for review

### Requirement: Extract available ComfyUI metadata without data loss
The platform SHALL attempt to extract workflow and image-embedded metadata from synchronized files, SHALL label unavailable fields as unknown, and SHALL allow manual correction of extracted fields.

#### Scenario: Metadata is embedded in an image
- **WHEN** a synchronized image contains readable prompt, workflow, model, seed, or generation metadata
- **THEN** the platform displays the extracted values and links them to the source image and snapshot

#### Scenario: Metadata is unavailable
- **WHEN** a synchronized file does not contain a requested metadata field
- **THEN** the platform displays that field as unknown and does not infer a value from unrelated files
