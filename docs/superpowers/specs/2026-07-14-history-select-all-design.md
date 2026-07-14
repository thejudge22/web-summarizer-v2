# History Select-All Design

**Date:** 2026-07-14  
**Status:** Approved for implementation

## Goal

Let a user quickly select every summary currently shown in the history sidebar
while selection mode is active.

## Behavior

- Selection mode displays a `Select all` control beside the existing selection
  controls.
- Activating it selects every summary in the currently rendered history list.
- Once every displayed summary is selected, its label becomes `Clear
  selection`.
- Activating `Clear selection` empties the selection.
- The selected count and existing ZIP-download/bulk-delete action bar update
  immediately in both directions.
- The control does not select records that are not presently listed in the
  sidebar.

## Implementation and verification

Keep selection state in the existing history controller; no API, database, or
route changes are required. Add a focused UI regression test covering the
control and its select-all/clear behavior, then run the full project test and
compilation checks.
