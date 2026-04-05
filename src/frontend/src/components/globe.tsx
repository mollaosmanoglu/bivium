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

const Globe = dynamic(() => import("react-globe.gl"), { ssr: false });

interface CameraPosition {
	lat: number;
	lng: number;
	altitude: number;
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
	properties: { faction_name: string; region_name: string; color: string };
	geometry: { type: string; coordinates: number[][][] | number[][][][] };
};

const STEP_DURATION = 4000;

export default function GlobeViewer({ timeline }: GlobeViewerProps) {
	const globeRef = useRef<GlobeMethods>(undefined) as MutableRefObject<
		GlobeMethods | undefined
	>;
	const [currentStep, setCurrentStep] = useState(-1);

	const polygons = useMemo<GeoFeature[]>(() => {
		if (!timeline || currentStep < 0) return [];
		const step = timeline.steps[currentStep];
		if (!step) return [];
		return step.regions.map((r) => ({
			type: "Feature",
			properties: {
				faction_name: r.faction_name,
				region_name: r.region_name,
				color: r.color,
			},
			geometry: r.geometry,
		}));
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
