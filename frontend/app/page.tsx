import VerificationDemo from "../components/VerificationDemo";
import { AboutModal } from "../components/AboutModal";
import ThemeToggle from "../components/theme/ThemeToggle";

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900 dark:bg-neutral-950 dark:text-neutral-100">
      <header className="flex items-center justify-between border-b bg-white px-6 py-4 dark:border-neutral-800 dark:bg-neutral-900">
        <h1 className="text-xl font-semibold">Dental Insurance Verification</h1>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <AboutModal />
        </div>
      </header>
      <VerificationDemo />
    </main>
  );
}
