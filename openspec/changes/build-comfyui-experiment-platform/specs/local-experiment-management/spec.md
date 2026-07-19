## ADDED Requirements

### Requirement: Create an experiment record
The platform SHALL allow the user to create an experiment with an original image and a user-provided goal or description, and SHALL assign a unique stable identifier to the experiment.

#### Scenario: Create experiment with original image
- **WHEN** the user selects an original image and submits a new experiment
- **THEN** the platform creates the local experiment record, stores the original image, and displays the experiment identifier and status

#### Scenario: Reject missing original image
- **WHEN** the user submits a new experiment without an original image
- **THEN** the platform SHALL not create the experiment and SHALL explain that an original image is required

### Requirement: Create an experiment workspace
The platform SHALL create a local artifact directory and a corresponding unique remote workspace path for each experiment, and SHALL display the paths needed for ComfyUI operations.

#### Scenario: Workspace is provisioned
- **WHEN** an experiment is created
- **THEN** the platform creates the local directory and records the remote workspace path without requiring the platform to run a ComfyUI workflow

#### Scenario: Reopen an experiment
- **WHEN** the user opens an existing experiment
- **THEN** the platform displays its status, snapshots, artifacts, evaluations, remote workspace path, and AI analysis history

### Requirement: Preserve experiment history
The platform SHALL keep snapshots, artifacts, evaluations, and analysis records associated with their experiment, and SHALL not replace earlier snapshots when a later sync occurs.

#### Scenario: Multiple snapshots are retained
- **WHEN** the user synchronizes the same experiment more than once
- **THEN** the platform creates an ordered new snapshot for each successful synchronization and keeps earlier snapshot artifacts addressable

#### Scenario: Local data remains available offline
- **WHEN** the AutoDL instance is unavailable after a previous synchronization
- **THEN** the user can still open local experiments, view synchronized images, and edit existing evaluations
