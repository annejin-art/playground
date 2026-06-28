"use client";

import { useEffect, useState, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ScraperStatus {
  name: string;
  last_run: string | null;
  status: string;
  items_found: number | null;
  error_message: string | null;
}

interface ScrapeRun {
  id: number;
  scraper_name: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  items_found: number | null;
  error_message: string | null;
}

function StatusBadge({ status }: { status: string }) {
  const color =
    status === "success"
      ? "bg-green-100 text-green-700"
      : status === "error"
      ? "bg-red-100 text-red-700"
      : status === "running"
      ? "bg-yellow-100 text-yellow-700"
      : "bg-gray-100 text-gray-500";
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${color}`}>
      {status}
    </span>
  );
}

export default function AdminPage() {
  const [scrapers, setScrapers] = useState<ScraperStatus[]>([]);
  const [runs, setRuns] = useState<ScrapeRun[]>([]);
  const [triggering, setTriggering] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    const [s, r] = await Promise.all([
      fetch(`${API}/api/admin/scrapers`).then((x) => x.json()).catch(() => []),
      fetch(`${API}/api/admin/runs`).then((x) => x.json()).catch(() => []),
    ]);
    setScrapers(s);
    setRuns(r.slice(0, 20));
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const triggerScraper = async (name: string) => {
    setTriggering(name);
    await fetch(`${API}/api/admin/scrapers/${name}/run`, { method: "POST" });
    setTimeout(() => {
      setTriggering(null);
      fetchData();
    }, 1500);
  };

  const triggerAll = async () => {
    setTriggering("all");
    await fetch(`${API}/api/admin/scrapers/run-all`, { method: "POST" });
    setTimeout(() => {
      setTriggering(null);
      fetchData();
    }, 1500);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <a href="/" className="text-sm text-blue-600 hover:underline">
              ← Back to RunDeals
            </a>
            <h1 className="text-xl font-bold text-gray-900 mt-1">Admin</h1>
          </div>
          <button
            onClick={triggerAll}
            disabled={triggering === "all"}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {triggering === "all" ? "Triggering..." : "Run All Scrapers"}
          </button>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden mb-6">
          <div className="px-4 py-3 border-b border-gray-100">
            <h2 className="text-sm font-semibold text-gray-700">Scrapers</h2>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">Items</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">Last Run</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              {scrapers.map((s) => (
                <tr key={s.name} className="border-b border-gray-50 last:border-0">
                  <td className="px-4 py-2.5 font-mono text-xs text-gray-700">{s.name}</td>
                  <td className="px-4 py-2.5">
                    <StatusBadge status={s.status} />
                  </td>
                  <td className="px-4 py-2.5 text-gray-500">{s.items_found ?? "—"}</td>
                  <td className="px-4 py-2.5 text-gray-400 text-xs">
                    {s.last_run ? new Date(s.last_run).toLocaleString() : "Never"}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <button
                      onClick={() => triggerScraper(s.name)}
                      disabled={triggering === s.name}
                      className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50"
                    >
                      {triggering === s.name ? "..." : "Run"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100">
            <h2 className="text-sm font-semibold text-gray-700">Recent Runs</h2>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">Scraper</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">Items</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">Started</th>
                <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">Duration</th>
              </tr>
            </thead>
            <tbody>
              {runs.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-gray-400 text-sm">
                    No runs yet
                  </td>
                </tr>
              )}
              {runs.map((r) => {
                const duration =
                  r.started_at && r.finished_at
                    ? `${((new Date(r.finished_at).getTime() - new Date(r.started_at).getTime()) / 1000).toFixed(1)}s`
                    : "—";
                return (
                  <tr key={r.id} className="border-b border-gray-50 last:border-0">
                    <td className="px-4 py-2.5 font-mono text-xs text-gray-700">{r.scraper_name}</td>
                    <td className="px-4 py-2.5">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="px-4 py-2.5 text-gray-500">{r.items_found ?? "—"}</td>
                    <td className="px-4 py-2.5 text-gray-400 text-xs">
                      {r.started_at ? new Date(r.started_at).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-gray-400 text-xs">{duration}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
