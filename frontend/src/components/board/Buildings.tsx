export const Roost = ({
  x,
  y,
  size,
}: {
  x: number;
  y: number;
  size: number;
}) => {
  return <rect x={x} y={y} width={size} height={size} fill="blue" />;
};

export const Sawmill = ({
  x,
  y,
  size,
}: {
  x: number;
  y: number;
  size: number;
}) => {
  return <rect x={x} y={y} width={size} height={size} fill="orange" />;
};
