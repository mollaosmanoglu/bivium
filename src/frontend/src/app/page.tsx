"use client";

import { useCallback, useRef, useState } from "react";
import GlobeViewer, { type AlternateTimeline } from "@/components/globe";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export default function Home() {
	const [question, setQuestion] = useState("");
	const [timeline, setTimeline] = useState<AlternateTimeline | null>(null);
	const [streaming, setStreaming] = useState(false);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const abortRef = useRef<AbortController | null>(null);

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
									<Button type="submit" disabled={loading} variant="secondary">
										{loading ? "..." : "Go"}
									</Button>
								</div>
								{error && <Badge variant="destructive">{error}</Badge>}
							</form>
						</CardContent>
					</Card>
				</div>
			)}

			{hasSteps && (
				<Button
					variant="ghost"
					className="absolute top-4 right-4 z-10 text-white/60 hover:text-white"
					onClick={() => {
						abortRef.current?.abort();
						setTimeline(null);
						setStreaming(false);
						setLoading(false);
					}}
				>
					New question
				</Button>
			)}
		</div>
	);
}
