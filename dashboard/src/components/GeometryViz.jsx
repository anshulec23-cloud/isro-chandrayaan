import React, { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Grid, Line } from '@react-three/drei';
import * as THREE from 'three';

function SpacecraftFrustum({ emissionAngle = 0 }) {
  const ref = useRef();
  
  useFrame((state) => {
    // Subtle hover animation
    ref.current.position.y = 5 + Math.sin(state.clock.elapsedTime) * 0.2;
  });

  // Calculate position based on emission angle (simplified: tilting from zenith)
  const angleRad = (emissionAngle * Math.PI) / 180;
  const distance = 5;
  const x = Math.sin(angleRad) * distance;
  const y = Math.cos(angleRad) * distance;

  return (
    <group ref={ref} position={[x, y, 0]} rotation={[0, 0, -angleRad]}>
      {/* Sensor Body */}
      <mesh position={[0, 0.5, 0]}>
        <boxGeometry args={[0.5, 1, 0.5]} />
        <meshBasicMaterial color="#ffc174" wireframe />
      </mesh>
      {/* Frustum (Field of View) */}
      <Line 
        points={[
          [0, 0, 0], [-1.5, -4, -1.5],
          [0, 0, 0], [1.5, -4, -1.5],
          [0, 0, 0], [1.5, -4, 1.5],
          [0, 0, 0], [-1.5, -4, 1.5],
          [-1.5, -4, -1.5], [1.5, -4, -1.5],
          [1.5, -4, -1.5], [1.5, -4, 1.5],
          [1.5, -4, 1.5], [-1.5, -4, 1.5],
          [-1.5, -4, 1.5], [-1.5, -4, -1.5]
        ]} 
        color="#ffc174" 
        lineWidth={1}
        transparent
        opacity={0.3}
      />
    </group>
  );
}

function SunVector({ incidence = 45, azimuth = 112 }) {
  // Convert incidence (angle from zenith) and azimuth to cartesian
  const incRad = (incidence * Math.PI) / 180;
  const azmRad = (azimuth * Math.PI) / 180;
  
  const distance = 8;
  const y = Math.cos(incRad) * distance;
  const x = Math.sin(incRad) * Math.sin(azmRad) * distance;
  const z = Math.sin(incRad) * Math.cos(azmRad) * distance;

  return (
    <group>
      <Line 
        points={[[0, 0, 0], [x, y, z]]}
        color="#ffffff"
        lineWidth={2}
        dashed
        dashScale={50}
        dashSize={0.2}
        dashOffset={0}
      />
      <mesh position={[x, y, z]}>
        <sphereGeometry args={[0.3, 16, 16]} />
        <meshBasicMaterial color="#ffffff" />
      </mesh>
      <directionalLight position={[x, y, z]} intensity={2} color="#ffffff" />
    </group>
  );
}

export default function GeometryViz({ incidence = 42.5, emission = 12.1, azimuth = 112.4 }) {
  return (
    <div className="w-full h-full bg-black">
      <Canvas camera={{ position: [8, 6, 8], fov: 45 }}>
        <color attach="background" args={['#000000']} />
        
        {/* Terrain Grid */}
        <Grid 
          infiniteGrid 
          fadeDistance={20} 
          cellColor="#333333" 
          sectionColor="#ffc174" 
          sectionThickness={1} 
          cellThickness={0.5} 
        />
        
        {/* Surface Plane for lighting reception */}
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]}>
          <planeGeometry args={[50, 50]} />
          <meshStandardMaterial color="#111111" roughness={0.9} />
        </mesh>
        
        <ambientLight intensity={0.1} />
        
        {/* Geometry Representations */}
        <SunVector incidence={incidence} azimuth={azimuth} />
        <SpacecraftFrustum emissionAngle={emission} />

        <OrbitControls 
          enablePan={false} 
          maxPolarAngle={Math.PI / 2 - 0.05} // Don't go below ground
          minDistance={5}
          maxDistance={15}
          autoRotate
          autoRotateSpeed={0.5}
        />
      </Canvas>
    </div>
  );
}
