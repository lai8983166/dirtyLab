## ADDED Requirements

### Requirement: Compare candidate images
The platform SHALL display multiple candidate images from an experiment or snapshot in a comparison view, and SHALL keep each candidate separately identifiable.

#### Scenario: Compare a candidate set
- **WHEN** the user selects two or more synchronized candidate images
- **THEN** the platform displays them together with their snapshot, workflow, and evaluation state

#### Scenario: Review one candidate
- **WHEN** the user opens a single candidate
- **THEN** the platform displays the image, original image when available, mask when available, source metadata, and all saved human and AI evaluation content

### Requirement: Record a complete candidate evaluation
The platform SHALL allow the user to record a result status of success, partial success, or failure; an overall satisfaction score from 1 through 10; configurable quality-dimension scores from 1 through 10; failure tags; and free-text notes for every candidate.

#### Scenario: Evaluate a failed candidate
- **WHEN** the user rates a candidate that did not meet the goal
- **THEN** the platform saves the failure status, overall score, selected failure tags, quality-dimension scores, and optional notes without requiring the candidate to be successful

#### Scenario: Save a partial evaluation
- **WHEN** the user saves only some fields for a candidate
- **THEN** the platform preserves the entered values, marks the evaluation incomplete, and allows completion later

### Requirement: Manage evaluation dimensions and failure tags
The platform SHALL provide default quality dimensions and failure tags, and SHALL allow the user to add, rename, disable, or reorder them for future evaluations without changing historical values.

#### Scenario: Customize a quality dimension
- **WHEN** the user adds or renames a quality dimension
- **THEN** the new template is available for later evaluations while earlier evaluations retain their original dimension label and score

#### Scenario: Use a fixed tag with extra explanation
- **WHEN** the user selects one or more failure tags and enters additional text
- **THEN** the platform stores both the structured tags and the free-text explanation on the candidate evaluation

### Requirement: Distinguish human evaluation from AI suggestions
The platform SHALL display human-entered scores and notes separately from unconfirmed AI suggestions, and SHALL record when an AI suggestion is accepted, edited, or rejected.

#### Scenario: Confirm an AI score suggestion
- **WHEN** the user accepts or edits a suggested score
- **THEN** the platform records the resulting value as user-confirmed and retains the original AI suggestion for provenance

#### Scenario: Reject an AI failure cause
- **WHEN** the user marks an AI-proposed failure cause as inaccurate
- **THEN** the platform records the rejection and does not include that cause in the confirmed evaluation
