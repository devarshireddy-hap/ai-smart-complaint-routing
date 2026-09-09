// Stores which department "portal" a MANAGEMENT_OFFICER has chosen for this
// browser session. This is a frontend-only convenience layered on top of
// backend authorization — it changes what an officer sees FIRST, not what
// they're authorized to access. The backend's assignment-based scoping
// (Final PSD Section 4: "Read complaints assigned to self") remains the
// real authorization boundary regardless of what's selected here.
//
// NOT part of the locked Final PSD — added at the team's request. See
// INTEGRATION_CHECKLIST.md for what this depends on from the backend.

import { OFFICER_PORTAL_STORAGE_KEY } from '../constants';

export function getSelectedDepartmentPortal() {
  try {
    const raw = sessionStorage.getItem(OFFICER_PORTAL_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setSelectedDepartmentPortal(department) {
  try {
    sessionStorage.setItem(OFFICER_PORTAL_STORAGE_KEY, JSON.stringify(department));
  } catch {
    // sessionStorage unavailable (e.g. privacy mode) — selection just won't
    // persist across a reload; the selector will ask again.
  }
}

export function clearSelectedDepartmentPortal() {
  try {
    sessionStorage.removeItem(OFFICER_PORTAL_STORAGE_KEY);
  } catch {
    // no-op
  }
}
