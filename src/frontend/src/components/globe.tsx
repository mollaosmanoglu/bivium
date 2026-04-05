"use client";

import dynamic from "next/dynamic";
import type { GlobeMethods } from "react-globe.gl";
import { useCallback, useEffect, useRef, useState, type MutableRefObject } from "react";
import { motion, AnimatePresence } from "motion/react";

const Globe = dynamic(() => import("react-globe.gl"), { ssr: false });

interface CountryHighlight {
  iso_a3: string;
  color: string;
  altitude: number;
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
  highlights: CountryHighlight[];
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

export default function GlobeViewer({ timeline }: GlobeViewerProps) {
  const globeRef = useRef<GlobeMethods>(undefined) as MutableRefObject<GlobeMethods | undefined>;
  const [countries, setCountries] = useState<GeoFeature[]>([]);
  const [currentStep, setCurrentStep] = useState(-1);
  const [highlightMap, setHighlightMap] = useState<Map<string, CountryHighlight>>(new Map());

  useEffect(() => {
    fetch("/data/countries-110m.geojson")
      .then((r) => r.json())
      .then((data) => setCountries(data.features));
  }, []);

  useEffect(() => {
    if (!timeline || currentStep < 0) return;

    const step = timeline.steps[currentStep];
    if (!step) return;

    const map = new Map<string, CountryHighlight>();
    for (const h of step.highlights) {
      map.set(h.iso_a3, h);
    }
    setHighlightMap(map);

    if (globeRef.current) {
      globeRef.current.pointOfView(step.camera, 1000);
    }
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
      const h = highlightMap.get(f.properties.ISO_A3);
      return h ? h.color : "rgba(200, 200, 200, 0.1)";
    },
    [highlightMap]
  );

  const getSideColor = useCallback(
    (feat: object) => {
      const f = feat as GeoFeature;
      const h = highlightMap.get(f.properties.ISO_A3);
      return h ? h.color : "rgba(150, 150, 150, 0.05)";
    },
    [highlightMap]
  );

  const getAltitude = useCallback(
    (feat: object) => {
      const f = feat as GeoFeature;
      const h = highlightMap.get(f.properties.ISO_A3);
      return h ? h.altitude : 0.005;
    },
    [highlightMap]
  );

  const step = timeline?.steps[currentStep];

  return (
    <div className="relative h-screen w-screen bg-black">
      <Globe
        ref={globeRef}
        globeImageUrl="//unpkg.com/three-globe/example/img/earth-dark.jpg"
        polygonsData={countries}
        polygonCapColor={getCapColor}
        polygonSideColor={getSideColor}
        polygonAltitude={getAltitude}
        polygonStrokeColor={() => "rgba(255, 255, 255, 0.1)"}
        polygonsTransitionDuration={800}
        enablePointerInteraction={false}
        backgroundColor="rgba(0,0,0,0)"
        atmosphereColor="#3a228a"
        atmosphereAltitude={0.25}
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
          <h2 className="text-white/80 text-xl font-medium">{timeline.title}</h2>
        </div>
      )}
    </div>
  );
}
