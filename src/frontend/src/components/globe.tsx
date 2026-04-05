"use client";

import { AnimatePresence, motion } from "motion/react";
import dynamic from "next/dynamic";
import {
	type MutableRefObject,
	useCallback,
	useEffect,
	useMemo,
	useRef,
	useState,
} from "react";
import type { GlobeMethods } from "react-globe.gl";

const Globe = dynamic(() => import("react-globe.gl"), { ssr: false });

interface Faction {
	name: string;
	color: string;
	countries: string[];
}

interface CameraPosition {
	lat: number;
	lng: number;
	altitude: number;
}

interface TimelineStep {
	year: number;
	narration: string;
	camera: CameraPosition;
	factions: Faction[];
}

export interface AlternateTimeline {
	title: string;
	steps: TimelineStep[];
}

interface GlobeViewerProps {
	timeline: AlternateTimeline | null;
}

type GeoFeature = {
	properties: { ISO_A3: string; NAME: string };
};

const STEP_DURATION = 4000;
const NEUTRAL_COLOR = "rgba(80, 80, 80, 0.3)";
const NEUTRAL_SIDE = "rgba(60, 60, 60, 0.2)";

export default function GlobeViewer({ timeline }: GlobeViewerProps) {
	const globeRef = useRef<GlobeMethods>(undefined) as MutableRefObject<
		GlobeMethods | undefined
	>;
	const [countries, setCountries] = useState<GeoFeature[]>([]);
	const [currentStep, setCurrentStep] = useState(-1);

	useEffect(() => {
		fetch("/data/countries-110m.geojson")
			.then((r) => r.json())
			.then((data) => setCountries(data.features));
	}, []);

	// Build a map: ISO_A3 -> { color, factionName }
	const colorMap = useMemo(() => {
		const map = new Map<string, { color: string; name: string }>();
		if (!timeline || currentStep < 0) return map;
		const step = timeline.steps[currentStep];
		if (!step) return map;
		for (const faction of step.factions) {
			for (const iso of faction.countries) {
				map.set(iso, { color: faction.color, name: faction.name });
			}
		}
		return map;
	}, [timeline, currentStep]);

	useEffect(() => {
		if (!timeline || currentStep < 0) return;
		const step = timeline.steps[currentStep];
		if (!step || !globeRef.current) return;
		globeRef.current.pointOfView(step.camera, 1000);
	}, [timeline, currentStep]);

	useEffect(() => {
		if (!timeline) {
			setCurrentStep(-1);
			return;
		}
		setCurrentStep(0);
		const interval = setInterval(() => {
			setCurrentStep((prev) => {
				if (prev >= timeline.steps.length - 1) {
					clearInterval(interval);
					return prev;
				}
				return prev + 1;
			});
		}, STEP_DURATION);
		return () => clearInterval(interval);
	}, [timeline]);

	const getCapColor = useCallback(
		(feat: object) => {
			const f = feat as GeoFeature;
			const entry = colorMap.get(f.properties.ISO_A3);
			return entry ? entry.color : NEUTRAL_COLOR;
		},
		[colorMap],
	);

	const getSideColor = useCallback(
		(feat: object) => {
			const f = feat as GeoFeature;
			const entry = colorMap.get(f.properties.ISO_A3);
			return entry ? `${entry.color}88` : NEUTRAL_SIDE;
		},
		[colorMap],
	);

	const getAltitude = useCallback(
		(feat: object) => {
			const f = feat as GeoFeature;
			return colorMap.has(f.properties.ISO_A3) ? 0.01 : 0.002;
		},
		[colorMap],
	);

	const getStrokeColor = useCallback(
		() => "rgba(0, 0, 0, 0.05)",
		[],
	);

	const getLabel = useCallback(
		(feat: object) => {
			const f = feat as GeoFeature;
			const entry = colorMap.get(f.properties.ISO_A3);
			if (entry) {
				return `<div style="text-align:center;padding:4px 8px;background:rgba(0,0,0,0.7);border-radius:4px;color:white">
					<b>${f.properties.NAME}</b><br/><span style="color:${entry.color}">${entry.name}</span>
				</div>`;
			}
			return `<div style="padding:4px 8px;background:rgba(0,0,0,0.7);border-radius:4px;color:gray">${f.properties.NAME}</div>`;
		},
		[colorMap],
	);

	const step = timeline?.steps[currentStep];

	return (
		<div className="relative h-screen w-screen bg-black">
			<Globe
				ref={globeRef}
				globeImageUrl="//cdn.jsdelivr.net/npm/three-globe/example/img/earth-night.jpg"
				backgroundImageUrl="//cdn.jsdelivr.net/npm/three-globe/example/img/night-sky.png"
				polygonsData={countries}
				polygonCapColor={getCapColor}
				polygonSideColor={getSideColor}
				polygonAltitude={getAltitude}
				polygonStrokeColor={getStrokeColor}
				polygonLabel={getLabel}
				polygonsTransitionDuration={800}
				atmosphereColor="#3a228a"
				atmosphereAltitude={0.2}
			/>

			<AnimatePresence mode="wait">
				{step && (
					<motion.div
						key={currentStep}
						initial={{ opacity: 0, y: 20 }}
						animate={{ opacity: 1, y: 0 }}
						exit={{ opacity: 0, y: -20 }}
						transition={{ duration: 0.5 }}
						className="absolute bottom-16 left-1/2 -translate-x-1/2 max-w-lg text-center"
					>
						<p className="text-white/60 text-sm font-mono">{step.year}</p>
						<p className="text-white text-lg mt-1">{step.narration}</p>
					</motion.div>
				)}
			</AnimatePresence>

			{timeline && (
				<div className="absolute top-8 left-1/2 -translate-x-1/2">
					<h2 className="text-white/80 text-xl font-medium">
						{timeline.title}
					</h2>
				</div>
			)}
		</div>
	);
}
