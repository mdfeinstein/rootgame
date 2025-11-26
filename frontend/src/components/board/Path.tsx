// Straight line link. Replace with path/quadratic for curves.
export function Path({
  a,
  b,
  stroke = "currentColor",
}: {
  a: { x: number; y: number };
  b: { x: number; y: number };
  stroke?: string;
}) {
  return (
    <line
      x1={a.x}
      y1={a.y}
      x2={b.x}
      y2={b.y}
      strokeWidth={3}
      stroke={stroke}
      strokeLinecap="round"
    />
  );
}
