# Guest Parent Management

## Purpose

Guest Parent Management improves the guest/rental parent grid by filtering invalid rows and showing useful spark/lineage popups for guest entries.

## How it works

Guest parent cards use the same `.sparks-tooltip` hover system as owned parent cards. Hover and keyboard focus both open the popup, using existing viewport-safe positioning.

Delegated event binding on `#guest-parent-grid` keeps popups working after refresh or re-render.

## Filtering behavior

Guest-parent normalization:

- collapses duplicate entries from repeated API paths
- filters likely owned/veteran trained characters
- ignores unrelated directory/scenario arrays
- excludes pure friend support card rows
- keeps rental/succession/trained-character style rows

If a guest entry has basic character info but no factor data, fallback popup content is shown.

## Dependencies and interactions

This feature uses existing owned-parent spark rendering through `renderParentSparks(parent, imgId)`. It changes UI display and guest-grid data filtering, not career automation decisions.

## Verification

Refresh guest parents, hover or focus a guest parent card, and confirm the spark popup appears. Verify friend support cards do not appear as guest parents.
