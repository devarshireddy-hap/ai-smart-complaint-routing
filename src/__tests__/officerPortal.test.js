import { describe, it, expect, beforeEach } from 'vitest';
import {
  getSelectedDepartmentPortal,
  setSelectedDepartmentPortal,
  clearSelectedDepartmentPortal,
} from '../auth/officerPortal';

describe('officerPortal session storage helper', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it('returns null when nothing has been selected', () => {
    expect(getSelectedDepartmentPortal()).toBeNull();
  });

  it('stores and retrieves a selected department', () => {
    setSelectedDepartmentPortal({ department_id: 'd-1', department_name: 'Electrical' });
    expect(getSelectedDepartmentPortal()).toEqual({ department_id: 'd-1', department_name: 'Electrical' });
  });

  it('clears the selection', () => {
    setSelectedDepartmentPortal({ department_id: 'd-1', department_name: 'Electrical' });
    clearSelectedDepartmentPortal();
    expect(getSelectedDepartmentPortal()).toBeNull();
  });
});
