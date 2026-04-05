"use client";

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
import { Card, CardContent } from "@/components/ui/card";

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
	description: string;
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
}

type GeoFeature = {
	type: "Feature";
	properties: {
		key: string;
		faction_name: string;
		region_name: string;
		color: string;
	};
	geometry: { type: string; coordinates: number[][][] | number[][][][] };
};

const STEP_DURATION = 4000;

export default function GlobeViewer({ timeline }: GlobeViewerProps) {
	const globeRef = useRef<GlobeMethods>(undefined) as MutableRefObject<
		GlobeMethods | undefined
	>;
	const [currentStep, setCurrentStep] = useState(-1);

	// Pre-build all step polygons once when timeline arrives
	const allStepPolygons = useMemo<GeoFeature[][]>(() => {
		if (!timeline) return [];
		return timeline.steps.map((step) =>
			step.regions
				.filter((r) => r.geometry)
				.map((r) => ({
					type: "Feature" as const,
					properties: {
						key: `${r.faction_name}::${r.region_name}`,
						faction_name: r.faction_name,
						region_name: r.region_name,
						color: r.color,
					},
					geometry: r.geometry,
				})),
		);
	}, [timeline]);

	const polygons = currentStep >= 0 ? (allStepPolygons[currentStep] ?? []) : [];

	useEffect(() => {
		if (!timeline || currentStep < 0) return;
		const step = timeline.steps[currentStep];
		if (!step || !globeRef.current) return;
		globeRef.current.pointOfView(step.camera, 1000);
	}, [timeline, currentStep]);

	// Start on first step when timeline appears
	useEffect(() => {
		if (!timeline || timeline.steps.length === 0) {
			setCurrentStep(-1);
			return;
		}
		if (currentStep === -1) {
			setCurrentStep(0);
		}
	}, [timeline, timeline?.steps.length, currentStep]);

	// Auto-advance when new steps arrive
	useEffect(() => {
		if (!timeline || timeline.steps.length === 0) return;
		const interval = setInterval(() => {
			setCurrentStep((prev) => {
				if (prev >= timeline.steps.length - 1) return prev;
				return prev + 1;
			});
		}, STEP_DURATION);
		return () => clearInterval(interval);
	}, [timeline, timeline?.steps.length]);

	const step = timeline?.steps[currentStep];

	return (
		<div className="relative h-screen w-screen bg-black">
			<Globe
				ref={globeRef}
				globeImageUrl="//cdn.jsdelivr.net/npm/three-globe/example/img/earth-night.jpg"
				backgroundImageUrl="//cdn.jsdelivr.net/npm/three-globe/example/img/night-sky.png"
				polygonsData={polygons}
				polygonCapColor={(f: object) => (f as GeoFeature).properties.color}
				polygonSideColor={(f: object) =>
					`${(f as GeoFeature).properties.color}88`
				}
				polygonAltitude={0.01}
				polygonStrokeColor={() => "rgba(255, 255, 255, 0.12)"}
				polygonLabel={(f: object) => {
					const feat = f as GeoFeature;
					return `<div style="padding:4px 8px;background:rgba(0,0,0,0.7);border-radius:4px;color:white;text-align:center">
						<b>${feat.properties.faction_name}</b><br/>
						<span style="color:${feat.properties.color}">${feat.properties.region_name}</span>
					</div>`;
				}}
				polygonsTransitionDuration={800}
				atmosphereColor="#3a228a"
				atmosphereAltitude={0.2}
			/>

			{/* Title */}
			{timeline && (
				<div className="absolute top-8 left-1/2 -translate-x-1/2 z-10 pointer-events-none">
					<h2 className="text-title text-white/80">{timeline.title}</h2>
				</div>
			)}

			{/* Faction cards */}
			<AnimatePresence mode="wait">
				{step && (
					<motion.div
						key={`factions-${currentStep}`}
						initial={{ opacity: 0, x: -20 }}
						animate={{ opacity: 1, x: 0 }}
						exit={{ opacity: 0, x: -20 }}
						transition={{ duration: 0.5 }}
						className="absolute top-20 left-4 flex flex-col gap-2 max-h-[calc(100vh-16rem)] overflow-y-auto z-10"
					>
						{step.factions
							.filter((f) => f.leader !== "-")
							.map((faction) => (
								<Card
									key={faction.name}
									size="sm"
									className="bg-white/5 border-white/10 backdrop-blur-md w-64"
								>
									<CardContent className="flex items-start gap-2 p-0">
										<span
											className="mt-0.5 h-3 w-3 shrink-0 rounded-full"
											style={{ backgroundColor: faction.color }}
										/>
									<div className="min-w-0">
											<p className="text-label text-white truncate">
												{faction.name}
											</p>
											<p className="text-caption text-white/50 truncate">
												{faction.leader}
											</p>
											<p className="text-caption text-white/40 mt-0.5 line-clamp-2">
												{faction.description}
											</p>
										</div>
									</CardContent>
								</Card>
							))}
					</motion.div>
				)}
			</AnimatePresence>

			{/* Narration + horizontal timeline */}
			{timeline && timeline.steps.length > 0 && (
				<div className="absolute bottom-0 left-0 right-0 z-10 pb-8">
					{/* Narration text */}
					<AnimatePresence mode="wait">
						{step && (
							<motion.p
								key={`narration-${currentStep}`}
								initial={{ opacity: 0, y: 10 }}
								animate={{ opacity: 1, y: 0 }}
								exit={{ opacity: 0, y: -10 }}
								transition={{ duration: 0.4 }}
								className="text-body text-white text-center max-w-lg mx-auto mb-6 px-4"
							>
								{step.narration}
							</motion.p>
						)}
					</AnimatePresence>

					{/* Dot timeline */}
					<div className="flex items-center justify-center gap-0 px-12">
						{timeline.steps.map((s, i) => {
							const isActive = i === currentStep;
							const isPast = i < currentStep;
							return (
								<div key={s.year} className="flex items-center">
									{/* Connector line */}
									{i > 0 && (
										<motion.div
											className="h-px w-8 sm:w-12"
											initial={{ backgroundColor: "rgba(255,255,255,0.1)" }}
											animate={{
												backgroundColor: isPast || isActive
													? "rgba(255,255,255,0.4)"
													: "rgba(255,255,255,0.1)",
											}}
											transition={{ duration: 0.5 }}
										/>
									)}
									{/* Dot + year */}
									<button
										type="button"
										onClick={() => setCurrentStep(i)}
										className="flex flex-col items-center gap-1.5 cursor-pointer"
									>
										<motion.div
											className="rounded-full"
											animate={{
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
											transition={{ type: "spring", stiffness: 300, damping: 25 }}
										/>
										<motion.span
											className="text-caption font-mono"
											animate={{
												color: isActive
													? "rgba(255,255,255,0.9)"
													: "rgba(255,255,255,0.35)",
											}}
											transition={{ duration: 0.3 }}
										>
											{s.year}
										</motion.span>
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
