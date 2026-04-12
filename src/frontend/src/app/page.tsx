"use client";

import { Check, Plus, Share, Shuffle } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import GlobeViewer, { type AlternateTimeline } from "@/components/globe";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";

const SCENARIOS = [
	"What if the Roman Empire never fell?",
	"What if the Mongols took Vienna?",
	"What if the Ottoman Empire won WWI?",
	"What if China discovered the Americas before Columbus?",
	"What if the USSR survived past 1991?",
	"What if Napoleon won at Waterloo?",
	"What if the Library of Alexandria never burned?",
	"What if the Byzantines held Constantinople in 1453?",
	"What if the Aztecs defeated Cortés?",
	"What if the American Revolution failed?",
	"What if the Soviets landed on the Moon first?",
	"What if Alexander the Great lived another 20 years?",
	"What if the Black Death never happened?",
	"What if the Cuban Missile Crisis led to nuclear war?",
	"What if the Third Reich captured Moscow?",
] as const;

export default function Home() {
	const [question, setQuestion] = useState("");
	const [timeline, setTimeline] = useState<AlternateTimeline | null>(null);
	const [streaming, setStreaming] = useState(false);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [copied, setCopied] = useState(false);
	const abortRef = useRef<AbortController | null>(null);

	useEffect(() => {
		const params = new URLSearchParams(window.location.search);
		const q = params.get("q");
		if (q) setQuestion(q);
	}, []);

	const handleSubmit = useCallback(
		async (e: React.FormEvent) => {
			e.preventDefault();
			if (!question.trim() || loading) return;

			setLoading(true);
			setStreaming(true);
			setError(null);
			setTimeline(null);

			abortRef.current?.abort();
			const abort = new AbortController();
			abortRef.current = abort;

			try {
				const res = await fetch("http://localhost:8001/api/timeline/stream", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ question }),
					signal: abort.signal,
				});

				if (!res.ok) {
					const data = await res.json();
					throw new Error(data.detail || "Something went wrong");
				}

				const reader = res.body?.getReader();
				if (!reader) throw new Error("No response body");

				const decoder = new TextDecoder();
				let buf = "";

				while (true) {
					const { done, value } = await reader.read();
					if (done) break;

					buf += decoder.decode(value, { stream: true });
					const lines = buf.split("\n");
					buf = lines.pop() ?? "";

					for (const line of lines) {
						if (!line.startsWith("data: ")) continue;
						const payload = JSON.parse(line.slice(6));

						if (payload.type === "title") {
							setTimeline({ title: payload.title, steps: [] });
						} else if (payload.type === "step") {
							setTimeline((prev) => {
								if (!prev) return { title: "", steps: [payload] };
								return { ...prev, steps: [...prev.steps, payload] };
							});
						} else if (payload.type === "done") {
							setStreaming(false);
							setLoading(false);
						}
					}
				}
			} catch (err) {
				if ((err as Error).name !== "AbortError") {
					setError(
						err instanceof Error ? err.message : "Something went wrong",
					);
				}
			} finally {
				setLoading(false);
			}
		},
		[question, loading],
	);

	const hasSteps = timeline && timeline.steps.length > 0;

	return (
		<div className="relative h-screen w-screen bg-black overflow-hidden">
			{/* GitHub — always visible top-right */}
			{!hasSteps && (
				<a
					href="https://github.com/mollaosmanoglu"
					target="_blank"
					rel="noopener noreferrer"
					className="absolute top-4 right-4 z-20 flex items-center gap-1.5 text-white hover:underline underline-offset-4 transition-colors px-2 py-1"
				>
					<svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
						<path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
					</svg>
					<span className="text-xs font-medium">mollaosmanoglu</span>
				</a>
			)}

			<GlobeViewer
				timeline={hasSteps ? timeline : null}
				streaming={streaming}
			/>

			{!hasSteps && (
				<div className="absolute inset-0 flex items-center justify-center z-10">
					<Card className="bg-white/5 border-white/10 backdrop-blur-md w-full max-w-md mx-4">
						<CardContent className="pt-6">
							<form
								onSubmit={handleSubmit}
								className="flex flex-col items-center gap-4"
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
									<Button
										type="button"
										variant="ghost"
										size="icon"
										disabled={loading}
										onClick={() =>
											setQuestion(
												SCENARIOS[Math.floor(Math.random() * SCENARIOS.length)],
											)
										}
										className="text-white/60 hover:text-white hover:bg-white/10 shrink-0"
										aria-label="Surprise me with a random scenario"
									>
										<Shuffle className="h-4 w-4" />
									</Button>
									<Button type="submit" disabled={loading} variant="secondary">
										{loading ? <Spinner /> : "Go"}
									</Button>
								</div>
								{error && <Badge variant="destructive">{error}</Badge>}
							</form>
						</CardContent>
					</Card>
				</div>
			)}

			{hasSteps && (
				<div className="absolute top-4 right-4 z-10 flex items-center gap-1">
					<Button
						variant="ghost"
						size="icon"
						className="text-white/60 hover:text-white hover:bg-white/10"
						onClick={() => {
							const url = new URL(window.location.href);
							url.searchParams.set("q", question);
							navigator.clipboard.writeText(url.toString());
							setCopied(true);
							setTimeout(() => setCopied(false), 1500);
						}}
					>
						{copied ? (
							<Check className="h-4 w-4" />
						) : (
							<Share className="h-4 w-4" />
						)}
					</Button>
					<Button
						size="icon"
						className="bg-white/10 text-white hover:bg-white/20"
						onClick={() => {
							abortRef.current?.abort();
							setTimeline(null);
							setStreaming(false);
							setLoading(false);
						}}
					>
						<Plus className="h-4 w-4" />
					</Button>
					<a
						href="https://github.com/mollaosmanoglu"
						target="_blank"
						rel="noopener noreferrer"
						className="flex items-center gap-1.5 text-white hover:underline underline-offset-4 transition-colors px-2 py-1"
					>
						<svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
							<path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
						</svg>
						<span className="text-xs font-medium">mollaosmanoglu</span>
					</a>
				</div>
			)}
		</div>
	);
}
