import Navbar from './Navbar';
import Sidebar from './Sidebar';
import { useAuth } from '../auth/AuthContext';

export default function AppLayout({ children }) {
  const { role } = useAuth();

  return (
    <div className="min-h-screen bg-ink-50">
      <Navbar />
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6 sm:flex-row sm:px-6">
        <Sidebar role={role} />
        <main className="min-w-0 flex-1 space-y-6">{children}</main>
      </div>
    </div>
  );
}
