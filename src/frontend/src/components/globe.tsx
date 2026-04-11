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
	Network,
	Shield,
	Star,
	Swords,
	Tent,
	Vote,
} from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import dynamic from "next/dynamic";
import {
	type MutableRefObject,
	useEffect,
	useMemo,
	useRef,
	useState,
} from "react";
import type { GlobeMethods } from "react-globe.gl";
import { Badge } from "@/components/ui/badge";
import {
	Sheet,
	SheetContent,
	SheetHeader,
	SheetTitle,
	SheetDescription,
} from "@/components/ui/sheet";

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
						(() => {
							const GovIcon =
								GOVERNMENT_ICONS[selectedFaction.government_type] ?? Circle;
							const govLabel =
								GOVERNMENT_LABELS[selectedFaction.government_type] ??
								"Unaligned";
							return (
								<SheetHeader>
									<div className="flex items-center gap-2">
										<span
											className="h-3 w-3 rounded-full shrink-0"
											style={{ backgroundColor: selectedFaction.color }}
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
								</SheetHeader>
							);
						})()}
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
									<ul className="text-caption text-white/60 text-center mt-3 space-y-1">
										{step.key_events.map((event) => (
											<li key={event}>• {event}</li>
										))}
									</ul>
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
											className="h-px w-8 sm:w-12 transition-colors duration-500"
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
