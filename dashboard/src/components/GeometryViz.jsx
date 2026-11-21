import React, { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Grid, Line } from '@react-three/drei';
import * as THREE from 'three';

function SpacecraftFrustum({ emissionAngle = 0, sensor = 'TMC-2' }) {
  const ref = useRef();
  
  // Real geometric parameters:
  // Emission angle tilts the sensor line-of-sight from local vertical
  const emiRad = (emissionAngle * Math.PI) / 180;
  const altitude = 5.5; // scaled 100km lunar orbit
  const satX = Math.sin(emiRad) * altitude * 0.5;
  const satY = Math.cos(emiRad) * altitude;

  // Swath aspect on the ground (pushbroom swath is long & narrow)
  const halfWidth = sensor === 'OHRC' ? 0.6 : sensor === 'IIRS' ? 1.8 : 1.2;
  const halfLength = sensor === 'OHRC' ? 1.5 : sensor === 'IIRS' ? 3.0 : 2.4;

  const groundPts = [
    [-halfWidth, 0, -halfLength],
    [halfWidth, 0, -halfLength],
    [halfWidth, 0, halfLength],
    [-halfWidth, 0, halfLength],
  ];

  useFrame((state) => {
    if (ref.current) {
      // Subtle orbital motion
      ref.current.position.y = satY + Math.sin(state.clock.elapsedTime * 0.8) * 0.08;
    }
  });

  return (
    <group>
      {/* Spacecraft Body & Solar Arrays */}
      <group ref={ref} position={[satX, satY, 0]}>
        {/* Main Bus */}
        <mesh>
          <boxGeometry args={[0.5, 0.4, 0.5]} />
          <meshBasicMaterial color="#e8a33d" wireframe />
        </mesh>
        {/* Left Solar Panel */}
        <mesh position={[-0.7, 0, 0]}>
          <boxGeometry args={[0.7, 0.02, 0.4]} />
          <meshBasicMaterial color="#d49030" wireframe />
        </mesh>
        {/* Right Solar Panel */}
        <mesh position={[0.7, 0, 0]}>
          <boxGeometry args={[0.7, 0.02, 0.4]} />
          <meshBasicMaterial color="#d49030" wireframe />
        </mesh>
        {/* Optical Sensor Aperture */}
        <mesh position={[0, -0.25, 0]}>
          <cylinderGeometry args={[0.12, 0.16, 0.2, 8]} />
          <meshBasicMaterial color="#ffffff" wireframe />
        </mesh>

        {/* Projected 3D Footprint Pyramid Rays */}
        {groundPts.map((pt, i) => (
          <Line
            key={i}
            points={[[0, -0.25, 0], [pt[0] - satX, -satY, pt[2]]]}
            color="#e8a33d"
            lineWidth={1.2}
            transparent
            opacity={0.5}
          />
        ))}
      </group>

      {/* Ground Swath Polygon Outline */}
      <Line
        points={[
          groundPts[0],
          groundPts[1],
          groundPts[2],
          groundPts[3],
          groundPts[0],
        ]}
        color="#e8a33d"
        lineWidth={2}
      />

      {/* Ground Swath Surface Fill */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <planeGeometry args={[halfWidth * 2, halfLength * 2]} />
        <meshBasicMaterial color="#e8a33d" transparent opacity={0.12} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

function SunRayVector({ incidence = 39.06, azimuth = 69.56 }) {
  // Convert solar incidence (zenith angle) and azimuth to 3D Cartesian coordinates
  const incRad = (incidence * Math.PI) / 180;
  const azmRad = (azimuth * Math.PI) / 180;
  const distance = 8.0;

  const sunY = Math.cos(incRad) * distance;
  const sunX = Math.sin(incRad) * Math.sin(azmRad) * distance;
  const sunZ = Math.sin(incRad) * Math.cos(azmRad) * distance;

  return (
    <group>
      {/* Sun Marker Point */}
      <mesh position={[sunX, sunY, sunZ]}>
        <sphereGeometry args={[0.25, 12, 12]} />
        <meshBasicMaterial color="#ffffff" wireframe />
      </mesh>

      {/* Dashed Illumination Rays */}
      <Line
        points={[[sunX, sunY, sunZ], [0, 0, 0]]}
        color="#ffffff"
        lineWidth={1}
        dashed
        dashScale={20}
        dashSize={0.4}
        dashOffset={0}
        transparent
        opacity={0.6}
      />

      <directionalLight position={[sunX, sunY, sunZ]} intensity={1.5} color="#fff1db" />
    </group>
  );
}

export default function GeometryViz({
  incidence = 39.06,
  emission = 0.0,
  azimuth = 69.56,
  gsd = 5.48,
  sensor = 'TMC-2'
}) {
  return (
    <div className="relative w-full h-[380px] bg-[#050505] border border-[#222222] overflow-hidden">
      {/* HUD Telemetry Overlay */}
      <div className="absolute top-3 left-3 z-10 font-mono text-[10px] text-[#888888] bg-[#0a0a0a]/90 border border-[#222222] px-3 py-2 space-y-1 pointer-events-none">
        <div className="text-[#e8a33d] font-bold tracking-wider">
          WIRE FRAME SENSOR MODEL // {sensor}
        </div>
        <div>ORBIT ALT: <span className="text-[#cccccc]">~100.0 KM</span></div>
        <div>INCIDENCE (i): <span className="text-[#e8a33d] font-bold">{Number(incidence).toFixed(2)}°</span></div>
        <div>EMISSION (e): <span className="text-[#cccccc]">{Number(emission).toFixed(2)}°</span></div>
        <div>SOLAR AZIMUTH: <span className="text-[#cccccc]">{Number(azimuth).toFixed(2)}°</span></div>
        <div>NATIVE GSD: <span className="text-[#e8a33d]">{Number(gsd).toFixed(2)} M/PX</span></div>
      </div>

      <div className="absolute bottom-2 right-3 z-10 font-mono text-[9px] text-[#555555] pointer-events-none">
        DRAG TO ROTATE // SCROLL TO ZOOM // AUTO-ORBIT ACTIVE
      </div>

      <Canvas camera={{ position: [8, 5, 8], fov: 42 }}>
        <color attach="background" args={['#050505']} />
        
        {/* Wireframe Ground Grid */}
        <Grid
          infiniteGrid
          fadeDistance={25}
          cellColor="#1a1a1a"
          sectionColor="#333333"
          sectionThickness={1}
          cellThickness={0.6}
          cellSize={1}
          sectionSize={4}
        />

        {/* Ambient base lighting */}
        <ambientLight intensity={0.2} />

        {/* Real solar illumination vector */}
        <SunRayVector incidence={incidence} azimuth={azimuth} />

        {/* Real spacecraft body and projected field-of-view pyramid */}
        <SpacecraftFrustum emissionAngle={emission} gsd={gsd} sensor={sensor} />

        {/* Orbital controls */}
        <OrbitControls
          enablePan={false}
          maxPolarAngle={Math.PI / 2 - 0.05}
          minDistance={5}
          maxDistance={16}
          autoRotate
          autoRotateSpeed={0.4}
        />
      </Canvas>
    </div>
  );
}
