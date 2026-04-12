"use client";

import {
	Building,
	Building2,
	Church,
	Circle,
	Crown,
	Flame,
	Globe as GlobeIcon,
	type LucideIcon,
	MapPin,
	MessageCircle,
	Network,
	Send,
	Shield,
	Star,
	Swords,
	Tent,
	Vote,
} from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import dynamic from "next/dynamic";
import {
	type FormEvent,
	type MutableRefObject,
	useCallback,
	useEffect,
	useMemo,
	useRef,
	useState,
} from "react";
import type { GlobeMethods } from "react-globe.gl";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
	Sheet,
	SheetContent,
	SheetHeader,
	SheetTitle,
	SheetDescription,
} from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";

type GovernmentType =
	| "monarchy"
	| "republic"
	| "empire"
	| "democracy"
	| "theocracy"
	| "military_junta"
	| "communist"
	| "fascist"
	| "tribal"
	| "federation"
	| "city_state"
	| "protectorate"
	| "unaligned";

const GOVERNMENT_ICONS: Record<GovernmentType, LucideIcon> = {
	monarchy: Crown,
	republic: Building2,
	empire: GlobeIcon,
	democracy: Vote,
	theocracy: Church,
	military_junta: Swords,
	communist: Star,
	fascist: Flame,
	tribal: Tent,
	federation: Network,
	city_state: Building,
	protectorate: Shield,
	unaligned: Circle,
};

const GOVERNMENT_LABELS: Record<GovernmentType, string> = {
	monarchy: "Monarchy",
	republic: "Republic",
	empire: "Empire",
	democracy: "Democracy",
	theocracy: "Theocracy",
	military_junta: "Military Junta",
	communist: "Communist",
	fascist: "Fascist",
	tribal: "Tribal",
	federation: "Federation",
	city_state: "City-State",
	protectorate: "Protectorate",
	unaligned: "Unaligned",
};

const Globe = dynamic(() => import("react-globe.gl"), { ssr: false });

interface CameraPosition {
	lat: number;
	lng: number;
	altitude: number;
}

interface FactionInfo {
	name: string;
	color: string;
	leader: string;
	government_type: GovernmentType;
	capital: string;
	backstory: string;
	description: string;
	lat: number;
	lng: number;
}

interface MergedRegion {
	faction_name: string;
	region_name: string;
	color: string;
	geometry: {
		type: string;
		coordinates: number[][][] | number[][][][];
	};
}

interface TimelineStep {
	year: number;
	narration: string;
	key_events: string[];
	camera: CameraPosition;
	factions: FactionInfo[];
	regions: MergedRegion[];
}

export interface AlternateTimeline {
	title: string;
	steps: TimelineStep[];
}

interface GlobeViewerProps {
	timeline: AlternateTimeline | null;
	streaming?: boolean;
}

type GeoFeature = {
	type: "Feature";
	properties: {
		faction_name: string;
		region_name: string;
		color: string;
		idx: number;
	};
	geometry: { type: string; coordinates: number[][][] | number[][][][] };
};

export default function GlobeViewer({
	timeline,
	streaming = false,
}: GlobeViewerProps) {
	const globeRef = useRef<GlobeMethods>(undefined) as MutableRefObject<
		GlobeMethods | undefined
	>;
	const [currentStep, setCurrentStep] = useState(0);
	const [selectedFaction, setSelectedFaction] = useState<FactionInfo | null>(
		null,
	);
	const [eventsOpen, setEventsOpen] = useState(false);
	const [chatMode, setChatMode] = useState(false);
	const [chatHistory, setChatHistory] = useState<
		{ role: string; content: string }[]
	>([]);
	const [chatInput, setChatInput] = useState("");
	const [chatStreaming, setChatStreaming] = useState(false);
	const chatEndRef = useRef<HTMLDivElement>(null);

	// Reset chat when faction changes
	useEffect(() => {
		setChatMode(false);
		setChatHistory([]);
		setChatInput("");
	}, [selectedFaction]);

	// Auto-scroll to bottom when chat updates
	useEffect(() => {
		chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
	}, [chatHistory]);

	const handleChatSubmit = useCallback(
		async (e: FormEvent) => {
			e.preventDefault();
			if (!chatInput.trim() || chatStreaming || !selectedFaction || !timeline)
				return;
			const userMsg = chatInput.trim();
			setChatInput("");
			setChatHistory((prev) => [...prev, { role: "user", content: userMsg }]);
			setChatStreaming(true);
			setChatHistory((prev) => [...prev, { role: "assistant", content: "" }]);

			try {
				const step = timeline.steps[currentStep];
				const res = await fetch("http://localhost:8001/api/chat", {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						question: timeline.title,
						timeline_title: timeline.title,
						step_year: step.year,
						step_narration: step.narration,
						faction_name: selectedFaction.name,
						leader: selectedFaction.leader,
						government_type: selectedFaction.government_type,
						capital: selectedFaction.capital,
						backstory: selectedFaction.backstory,
						message: userMsg,
						history: chatHistory.filter((m) => m.content),
					}),
				});
				const reader = res.body?.getReader();
				if (!reader) return;
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
						if (payload.done) break;
						if (payload.text) {
							setChatHistory((prev) => {
								const updated = [...prev];
								const last = updated[updated.length - 1];
								if (last && last.role === "assistant") {
									updated[updated.length - 1] = {
										...last,
										content: last.content + payload.text,
									};
								}
								return updated;
							});
						}
					}
				}
			} finally {
				setChatStreaming(false);
			}
		},
		[chatInput, chatStreaming, selectedFaction, timeline, currentStep, chatHistory],
	);

	const allStepPolygons = useMemo<GeoFeature[][]>(() => {
		if (!timeline) return [];
		return timeline.steps.map((step) =>
			step.regions
				.filter((r) => r.geometry)
				.map((r, i) => ({
					type: "Feature" as const,
					properties: {
						faction_name: r.faction_name,
						region_name: r.region_name,
						color: r.color,
						idx: i,
					},
					geometry: r.geometry,
				})),
		);
	}, [timeline]);

	const polygons = allStepPolygons[currentStep] ?? [];
	const step = timeline?.steps[currentStep];
	const factionLabels = useMemo(
		() =>
			step?.factions.filter((f) => f.leader !== "-" && f.lat !== 0) ?? [],
		[step],
	);

	// Camera + auto-rotate on home screen
	useEffect(() => {
		const globe = globeRef.current;
		if (!globe) return;
		const controls = globe.controls();
		if (!timeline) {
			controls.autoRotate = true;
			controls.autoRotateSpeed = 0.4;
			globe.pointOfView({ lat: 20, lng: 0, altitude: 2.0 }, 0);
		} else {
			controls.autoRotate = false;
			const s = timeline.steps[currentStep];
			if (s) globe.pointOfView(s.camera, 1000);
		}
	}, [timeline, currentStep]);

	// Ensure auto-rotate starts after globe mounts
	useEffect(() => {
		if (timeline) return;
		const id = setTimeout(() => {
			const globe = globeRef.current;
			if (!globe) return;
			const controls = globe.controls();
			controls.autoRotate = true;
			controls.autoRotateSpeed = 0.4;
			globe.pointOfView({ lat: 20, lng: 0, altitude: 2.0 }, 0);
		}, 500);
		return () => clearTimeout(id);
	}, [timeline]);

	// Streaming: follow latest step
	useEffect(() => {
		if (!streaming || !timeline) return;
		setCurrentStep(timeline.steps.length - 1);
	}, [streaming, timeline?.steps.length]);

	// Collapse key events when step changes
	useEffect(() => {
		setEventsOpen(false);
	}, [currentStep]);

	// After streaming ends, stay on the last step

	return (
		<div className="relative h-screen w-screen bg-black">
			<Globe
				ref={globeRef}
				globeImageUrl="//cdn.jsdelivr.net/npm/three-globe/example/img/earth-night.jpg"
				backgroundImageUrl="//cdn.jsdelivr.net/npm/three-globe/example/img/night-sky.png"
				polygonsData={polygons}
				polygonCapColor={(f: object) => (f as GeoFeature).properties.color}
				polygonSideColor={() => "rgba(0, 0, 0, 0)"}
				polygonAltitude={(f: object) =>
					0.006 + (f as GeoFeature).properties.idx * 0.0002
				}
				polygonStrokeColor={() => "rgba(0, 0, 0, 0)"}
				polygonLabel={(f: object) => {
					const feat = f as GeoFeature;
					const faction = step?.factions.find(
						(fac) => fac.name === feat.properties.faction_name,
					);
					const govLine = faction
						? `<div style="color:rgba(255,255,255,0.5);font-size:11px;text-transform:capitalize;margin-top:2px">${faction.government_type.replace("_", " ")}</div>`
						: "";
					const leaderLine =
						faction && faction.leader !== "-"
							? `<div style="color:rgba(255,255,255,0.8);font-size:12px;margin-top:2px">${faction.leader}</div>`
							: "";
					return `<div style="padding:6px 10px;background:rgba(0,0,0,0.8);border-radius:4px;color:white;text-align:center;min-width:120px">
						<b>${feat.properties.faction_name}</b>
						${govLine}
						${leaderLine}
						<div style="color:${feat.properties.color};font-size:11px;margin-top:4px">${feat.properties.region_name}</div>
					</div>`;
				}}
				polygonsTransitionDuration={0}
				htmlElementsData={factionLabels}
				htmlLat={(d: object) => (d as FactionInfo).lat}
				htmlLng={(d: object) => (d as FactionInfo).lng}
				htmlAltitude={0.02}
				htmlElement={(d: object) => {
					const f = d as FactionInfo;
					const el = document.createElement("div");
					el.style.cssText =
						"pointer-events:none;text-align:center;white-space:nowrap;";
					el.innerHTML = `<span style="color:white;font-weight:600;font-size:13px;text-shadow:0 0 6px rgba(0,0,0,0.9),0 0 12px rgba(0,0,0,0.6)">${f.name}</span>`;
					return el;
				}}
				htmlTransitionDuration={0}
				onPolygonClick={(f: object) => {
					const feat = f as GeoFeature;
					const faction = step?.factions.find(
						(fac) => fac.name === feat.properties.faction_name,
					);
					if (faction) setSelectedFaction(faction);
				}}
				atmosphereColor="#3a228a"
				atmosphereAltitude={0.2}
			/>

			{/* Title */}
			{timeline && (
				<div className="absolute top-8 left-1/2 -translate-x-1/2 z-10 pointer-events-none">
					<h2 className="text-title text-white/80">{timeline.title}</h2>
				</div>
			)}

			{/* Faction detail sheet */}
			<Sheet
				open={!!selectedFaction}
				onOpenChange={(open: boolean) => !open && setSelectedFaction(null)}
			>
				<SheetContent
					side="left"
					className="bg-black/90 border-white/10 text-white w-80"
				>
					{selectedFaction &&
						(chatMode ? (
							<div className="flex flex-col h-[calc(100vh-2rem)] pt-8 px-4">
								<SheetTitle className="text-white text-sm mb-3 shrink-0">
									{selectedFaction.leader}
								</SheetTitle>
								<ScrollArea className="flex-1 min-h-0 pr-2">
									{chatHistory.map((msg, i) => (
										<div
											key={i}
											className={`mb-3 ${msg.role === "user" ? "text-right" : ""}`}
										>
											{msg.role === "assistant" && !msg.content && chatStreaming ? (
												<div className="inline-flex gap-1 px-3 py-2 rounded-lg bg-white/5">
													<span className="h-1.5 w-1.5 rounded-full bg-white/40 animate-bounce [animation-delay:0ms]" />
													<span className="h-1.5 w-1.5 rounded-full bg-white/40 animate-bounce [animation-delay:150ms]" />
													<span className="h-1.5 w-1.5 rounded-full bg-white/40 animate-bounce [animation-delay:300ms]" />
												</div>
											) : (
												<p
													className={`text-sm inline-block px-3 py-2 rounded-lg ${
														msg.role === "user"
															? "bg-white/10 text-white"
															: "bg-white/5 text-white/80"
													}`}
												>
													{msg.content}
												</p>
											)}
										</div>
									))}
									<div ref={chatEndRef} />
								</ScrollArea>
								<Separator className="my-2 bg-white/10 shrink-0" />
								<form
									onSubmit={handleChatSubmit}
									className="flex gap-2 shrink-0 pb-4"
								>
									<Textarea
										value={chatInput}
										onChange={(e) => setChatInput(e.target.value)}
										onKeyDown={(e) => {
											if (e.key === "Enter" && !e.shiftKey) {
												e.preventDefault();
												handleChatSubmit(e);
											}
										}}
										placeholder="Ask a question..."
										className="bg-white/5 border-white/10 text-white text-sm min-h-[40px] max-h-[80px] resize-none"
									/>
									<Button
										type="submit"
										size="icon"
										disabled={chatStreaming || !chatInput.trim()}
										className="shrink-0"
									>
										<Send className="h-4 w-4" />
									</Button>
								</form>
							</div>
						) : (
							(() => {
								const GovIcon =
									GOVERNMENT_ICONS[selectedFaction.government_type] ??
									Circle;
								const govLabel =
									GOVERNMENT_LABELS[selectedFaction.government_type] ??
									"Unaligned";
								return (
									<SheetHeader>
										<div className="flex items-center gap-2">
											<span
												className="h-3 w-3 rounded-full shrink-0"
												style={{
													backgroundColor: selectedFaction.color,
												}}
											/>
											<SheetTitle className="text-white">
												{selectedFaction.name}
											</SheetTitle>
										</div>
										<div className="flex items-center gap-2 mt-1">
											<Badge
												variant="secondary"
												className="bg-white/10 text-white/80 border-white/10 gap-1"
											>
												<GovIcon className="h-3 w-3" />
												{govLabel}
											</Badge>
											{selectedFaction.capital &&
												selectedFaction.capital !== "-" && (
													<span className="flex items-center gap-1 text-xs text-white/60">
														<MapPin className="h-3 w-3" />
														{selectedFaction.capital}
													</span>
												)}
										</div>
										<SheetDescription className="text-white/50">
											{selectedFaction.leader !== "-" && (
												<span className="block text-white/70 mb-1">
													{selectedFaction.leader}
												</span>
											)}
											{selectedFaction.description}
										</SheetDescription>
										{selectedFaction.backstory && (
											<p className="border-l-2 border-white/10 pl-3 mt-3 text-sm text-white/60 leading-relaxed">
												{selectedFaction.backstory}
											</p>
										)}
										{selectedFaction.leader !== "-" &&
											!streaming &&
											timeline &&
											currentStep === timeline.steps.length - 1 && (
												<Button
													variant="ghost"
													size="sm"
													className="mt-4 text-white/60 hover:text-white/90 hover:bg-white/5"
													onClick={() => setChatMode(true)}
												>
													<MessageCircle className="h-4 w-4 mr-1" />
													Talk to {selectedFaction.leader}
												</Button>
											)}
									</SheetHeader>
								);
							})()
						))}
				</SheetContent>
			</Sheet>

			{/* Narration + timeline */}
			{timeline && timeline.steps.length > 0 && (
				<div className="absolute bottom-0 left-0 right-0 z-10 pb-8 pointer-events-none">
					<AnimatePresence mode="wait">
						{step && (
							<motion.div
								key={`narration-${currentStep}`}
								initial={{ opacity: 0, y: 10 }}
								animate={{ opacity: 1, y: 0 }}
								exit={{ opacity: 0, y: -10 }}
								transition={{ duration: 0.4 }}
								className="max-w-lg mx-auto mb-6 px-4"
							>
								<p className="text-body text-white text-center">
									{step.narration}
								</p>
								{step.key_events && step.key_events.length > 0 && (
									<div className="text-center mt-2 pointer-events-auto">
										<button
											type="button"
											onClick={() => setEventsOpen((o) => !o)}
											className="text-caption text-white/40 hover:text-white/70 transition-colors"
										>
											{eventsOpen ? "Hide events ▴" : "Key events ▾"}
										</button>
										<AnimatePresence>
											{eventsOpen && (
												<motion.ul
													initial={{ opacity: 0, height: 0 }}
													animate={{ opacity: 1, height: "auto" }}
													exit={{ opacity: 0, height: 0 }}
													transition={{ duration: 0.3 }}
													className="text-caption text-white/60 text-center mt-2 space-y-1 overflow-hidden"
												>
													{step.key_events.map((event) => (
														<li key={event}>• {event}</li>
													))}
												</motion.ul>
											)}
										</AnimatePresence>
									</div>
								)}
							</motion.div>
						)}
					</AnimatePresence>

					<div className="flex items-center justify-center gap-0 px-12 pointer-events-auto">
						{timeline.steps.map((s, i) => {
							const isActive = i === currentStep;
							const isPast = i < currentStep;
							return (
								<div key={s.year} className="flex items-center">
									{i > 0 && (
										<div
											className="h-px w-12 sm:w-20 transition-colors duration-500"
											style={{
												backgroundColor:
													isPast || isActive
														? "rgba(255,255,255,0.4)"
														: "rgba(255,255,255,0.1)",
											}}
										/>
									)}
									<button
										type="button"
										onClick={() => setCurrentStep(i)}
										className="flex flex-col items-center gap-1.5 cursor-pointer"
									>
										<div
											className="rounded-full transition-all duration-300"
											style={{
												width: isActive ? 12 : 8,
												height: isActive ? 12 : 8,
												backgroundColor: isActive
													? "#ffffff"
													: isPast
														? "rgba(255,255,255,0.5)"
														: "rgba(255,255,255,0.2)",
												boxShadow: isActive
													? "0 0 12px rgba(255,255,255,0.4)"
													: "none",
											}}
										/>
										<span
											className="text-caption font-mono transition-colors duration-300"
											style={{
												color: isActive
													? "rgba(255,255,255,0.9)"
													: "rgba(255,255,255,0.35)",
											}}
										>
											{s.year}
										</span>
									</button>
								</div>
							);
						})}
					</div>
				</div>
			)}
		</div>
	);
}
