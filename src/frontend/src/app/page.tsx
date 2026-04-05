"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import GlobeViewer, { type AlternateTimeline } from "@/components/globe";

export default function Home() {
  const [question, setQuestion] = useState("");
  const [timeline, setTimeline] = useState<AlternateTimeline | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || loading) return;

    setLoading(true);
    setError(null);
    setTimeline(null);

    try {
      const res = await fetch("http://localhost:8001/api/timeline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Something went wrong");
      }

      const data: AlternateTimeline = await res.json();
      setTimeline(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative h-screen w-screen bg-black overflow-hidden">
      <GlobeViewer timeline={timeline} />

      {!timeline && (
        <div className="absolute inset-0 flex items-center justify-center z-10">
          <form
            onSubmit={handleSubmit}
            className="flex flex-col items-center gap-4 w-full max-w-md px-4"
          >
            <h1 className="text-white text-3xl font-semibold tracking-tight">
              What if...
            </h1>
            <div className="flex w-full gap-2">
              <Input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="the Roman Empire never fell?"
                className="bg-white/10 border-white/20 text-white placeholder:text-white/40"
                disabled={loading}
              />
              <Button type="submit" disabled={loading} variant="secondary">
                {loading ? "..." : "Go"}
              </Button>
            </div>
            {error && (
              <p className="text-red-400 text-sm">{error}</p>
            )}
          </form>
        </div>
      )}
    </div>
  );
}
