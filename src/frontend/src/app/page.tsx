"use client";

import { useState } from "react";
import GlobeViewer, { type AlternateTimeline } from "@/components/globe";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

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

			{timeline && (
				<Button
					variant="ghost"
					className="absolute top-4 right-4 z-10 text-white/60 hover:text-white"
					onClick={() => setTimeline(null)}
				>
					New question
				</Button>
			)}
		</div>
	);
}
