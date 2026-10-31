import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import api from "../api/client";

export default function Landing() {
  const [backend, setBackend] = useState({ state: "loading", db: null });

  useEffect(() => {
    let active = true;

    api
      .get("/api/v1/health")
      .then(({ data }) => {
        if (active) {
          setBackend({ state: "online", db: data.db });
        }
      })
      .catch(() => {
        if (active) {
          setBackend({ state: "offline", db: null });
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const backendLabel =
    backend.state === "loading"
      ? "Checking backend…"
      : backend.state === "online"
        ? `Backend online · database ${backend.db}`
        : "Backend unavailable";

  return (
    <main className="min-h-screen bg-gradient-to-br from-emerald-50 via-white to-sky-50">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <span className="text-lg font-bold tracking-tight text-emerald-800">
          Volunteer NGO Platform
        </span>
        <div className="flex items-center gap-4 text-sm font-medium">
          <Link className="text-slate-600 hover:text-emerald-700" to="/login">
            Log in
          </Link>
          <Link
            className="rounded-full bg-emerald-700 px-4 py-2 text-white shadow-sm hover:bg-emerald-800"
            to="/register"
          >
            Register
          </Link>
        </div>
      </nav>

      <section className="mx-auto grid max-w-6xl gap-10 px-6 pb-24 pt-20 md:grid-cols-2 md:items-center">
        <div>
          <p className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-emerald-700">
            Connect · coordinate · contribute
          </p>
          <h1 className="max-w-xl text-5xl font-bold tracking-tight text-slate-900 md:text-6xl">
            Make meaningful impact together.
          </h1>
          <p className="mt-6 max-w-lg text-lg leading-8 text-slate-600">
            A shared space for volunteers, NGOs, donors, and beneficiaries to turn
            community support into coordinated action.
          </p>
          <div className="mt-8 flex flex-wrap gap-4">
            <Link
              className="rounded-lg bg-emerald-700 px-5 py-3 font-semibold text-white hover:bg-emerald-800"
              to="/register"
            >
              Get started
            </Link>
            <Link
              className="rounded-lg border border-slate-300 bg-white px-5 py-3 font-semibold text-slate-700 hover:border-emerald-500 hover:text-emerald-700"
              to="/login"
            >
              I already have an account
            </Link>
          </div>
        </div>

        <div className="rounded-3xl border border-emerald-100 bg-white/80 p-8 shadow-xl shadow-emerald-900/5">
          <p className="text-sm font-semibold text-slate-500">System status</p>
          <div className="mt-5 flex items-center gap-3">
            <span
              aria-hidden="true"
              className={`h-3 w-3 rounded-full ${backend.state === "online" ? "bg-emerald-500" : backend.state === "offline" ? "bg-rose-500" : "animate-pulse bg-amber-400"}`}
            />
            <p className="font-medium text-slate-800">{backendLabel}</p>
          </div>
          <p className="mt-6 border-t border-slate-100 pt-6 text-sm leading-6 text-slate-500">
            This connectivity check is powered by the FastAPI health endpoint.
            Feature workflows will be added in the next project phases.
          </p>
        </div>
      </section>
    </main>
  );
}
