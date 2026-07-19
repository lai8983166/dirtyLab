## ADDED Requirements

### Requirement: Configure a multimodal analysis provider
The platform SHALL allow the user to configure one third-party multimodal model endpoint and model identifier, SHALL store the API credential only in local configuration, and SHALL never include the credential in experiment records or logs.

#### Scenario: Configure provider credentials
- **WHEN** the user enters a valid endpoint, model identifier, and API credential
- **THEN** the platform stores the provider configuration locally and indicates that analysis is available

#### Scenario: Missing provider configuration
- **WHEN** the user requests analysis without a complete provider configuration
- **THEN** the platform explains what configuration is missing and does not send experiment data

### Requirement: Trigger analysis explicitly
The platform SHALL request multimodal analysis only after the user explicitly triggers it for a selected candidate or comparison set.

#### Scenario: Analyze a candidate on request
- **WHEN** the user clicks request AI analysis for a candidate
- **THEN** the platform sends the selected images, goal, available workflow and metadata, and relevant confirmed evaluation context to the configured multimodal model

#### Scenario: Synchronization does not call AI
- **WHEN** the user synchronizes a new snapshot
- **THEN** the platform stores the artifacts without making an automatic third-party model request

### Requirement: Store editable AI analysis
The platform SHALL store the provider/model, request time, request context, response, failure-cause suggestions, score suggestions, and next-step suggestions as an editable unconfirmed analysis associated with the experiment and candidate.

#### Scenario: Analysis succeeds
- **WHEN** the multimodal model returns a valid response
- **THEN** the platform displays the response as an editable draft and preserves the original response for provenance

#### Scenario: Analysis fails
- **WHEN** the provider times out, rejects the request, or returns an invalid response
- **THEN** the platform records a user-visible failure state without creating confirmed scores or causes

### Requirement: Confirm analysis selectively
The platform SHALL let the user edit, accept, or reject individual AI suggestions, and SHALL distinguish confirmed user decisions from unconfirmed model output.

#### Scenario: Confirm edited suggestions
- **WHEN** the user edits a suggested failure cause or quality score and confirms it
- **THEN** the platform saves the edited value as user-confirmed and retains the unedited suggestion as provenance

#### Scenario: Keep analysis unconfirmed
- **WHEN** the user closes an analysis without confirming it
- **THEN** the platform preserves it as an unconfirmed draft and does not treat it as ground-truth evaluation data
