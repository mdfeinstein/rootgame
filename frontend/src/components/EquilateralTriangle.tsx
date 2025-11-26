import React from "react";

type Props = {
  cx: number; // center x (SVG coordinates)
  cy: number; // center y (SVG coordinates)
  r: number; // circumradius (distance from center to each vertex)
  rotationDeg?: number; // rotation in degrees (default -90 so one point faces up)
  stroke?: string;
  strokeWidth?: number;
  fill?: string;
  // Optional: explicit svg width/height; if omitted we set viewBox to include triangle
  svgWidth?: number;
  svgHeight?: number;
};

function degToRad(deg: number) {
  return (deg * Math.PI) / 180;
}

export const EquilateralTriangle: React.FC<Props> = ({
  cx,
  cy,
  r,
  rotationDeg = -90, // default: point-up
  stroke = "black",
  strokeWidth = 2,
  fill = "none",
  svgWidth,
  svgHeight,
}) => {
  // compute 3 vertices at rotation, rotation+120, rotation+240 degrees
  const angles = [rotationDeg, rotationDeg + 120, rotationDeg + 240];
  const points = angles
    .map((deg) => {
      const a = degToRad(deg);
      const x = cx + r * Math.cos(a);
      const y = cy + r * Math.sin(a);
      return `${x},${y}`;
    })
    .join(" ");

  // If svg width/height not provided, create a viewBox that comfortably contains the triangle.
  // We'll use bounding box of the circumscribed circle: [cx - r, cy - r, 2r, 2r]
  const viewBox = `${cx - r} ${cy - r} ${2 * r} ${2 * r}`;

  return (
    <polygon
      points={points}
      stroke={stroke}
      strokeWidth={strokeWidth}
      fill={fill}
    />
  );
};

export default EquilateralTriangle;
