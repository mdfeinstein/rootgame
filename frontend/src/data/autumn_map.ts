// this is the autumn map. reference here: https://www.therootdatabase.com/map/autumn/

export const suitMap: Record<number, string> = {
  1: "red",
  2: "orange",
  3: "yellow",
  4: "yellow",
  5: "yellow",
  6: "red",
  7: "orange",
  8: "red",
  9: "orange",
  10: "yellow",
  11: "orange",
  12: "red",
};

// positions of clearings in the autumn map, realitve to width and height
export const defaultPositions = [
    { x: 0.2, y: 0.2},
    { x: 0.8, y: 0.3 },
    { x: 0.8 , y: 0.8  },
    { x: 0.2 , y: 0.8  },
    { x: 0.55 , y: 0.2 },
    { x: 0.85 , y: 0.5  },
    { x: 0.6 , y: 0.7  },
    { x: 0.4 , y: 0.85  },
    { x: 0.15 , y: 0.4 },
    { x: 0.4 , y: 0.35  },
    { x: 0.6 , y: 0.5  },
    { x: 0.4 , y: 0.6 },
  ];

export const defaultLinks : { from: number, to: number }[] = [
  { from: 1, to: 10 },
  { from: 1, to: 5 },
  { from: 1, to: 9 },
  { from: 2, to: 5 },
  { from: 2, to: 10 },
  { from: 2, to: 6 },
  { from: 3, to: 6 },
  { from: 3, to: 7 },
  { from: 3, to: 11 },
  { from: 4, to: 12 },
  { from: 4, to: 8 },
  { from: 4, to: 9 },
  { from: 10, to: 12 },
  { from: 11, to: 12 },
  { from: 11, to: 6 },
  { from: 7, to: 8 },
  { from: 12, to: 9 },
  { from: 12, to: 7 },
];
export const waterLinks = [
  { from: 4, to: 7 },
  { from: 7, to: 11 },
  { from: 11, to: 10 },
  { from: 10, to: 5 },
];

type SquareProps = { x: number; y: number; size: number };
const sq_size = 0.3;
export const buildingSlotMap: Record<number, SquareProps[]> = {
  1: [{ x: -0.2, y: 0, size: sq_size }],
  2: [
    { x: -0.1, y: -0.1, size: sq_size },
    { x: 0.2, y: 0.3, size: sq_size },
  ],
  3: [{ x: -0.2, y: -0.1, size: sq_size }],
  4: [{ x: 0.4, y: -0.1, size: sq_size }],
  5: [
    { x: -0.3, y: -0.1, size: sq_size },
    { x: 0.3, y: -0.15, size: sq_size },
  ],
  6: [
    { x: 0.1, y: -0.3, size: sq_size },
    { x: -0.3, y: 0.1, size: sq_size },
  ],
  7: [
    { x: 0, y: -0.5, size: sq_size },
    { x: -0.3, y: 0.2, size: sq_size },
  ],
  8: [
    { x: 0.3, y: -0.4, size: sq_size },
    { x: 0.1, y: 0.2, size: sq_size },
  ],
  9: [
    { x: 0.3, y: -0.4, size: sq_size },
    { x: -0.2, y: 0.45, size: sq_size },
  ],
  10: [
    { x: -0.4, y: -0.3, size: sq_size },
    { x: 0.2, y: 0.45, size: sq_size },
  ],
  11: [
    { x: -0.3, y: -0.3, size: sq_size },
    { x: 0.2, y: 0.0, size: sq_size },
    { x: -0.35, y: 0.3, size: sq_size },
  ],
  12: [
    { x: 0.45, y: 0, size: sq_size },
    { x: -0.1, y: 0.45, size: sq_size },
  ],
};

export const warriorSlotMap: Record<number, SquareProps[]> = {
  1: [
    { x: -0.4, y: -0.4, size: sq_size },
    { x: -0.4, y: 0.4, size: sq_size },
    { x: 0.4, y: 0.4, size: sq_size },
    { x: 0.4, y: -0.4, size: sq_size },
  ],
  2: [
    { x: -0.45, y: -0.45, size: sq_size },
    { x: -0.4, y: 0.4, size: sq_size },
    { x: 0.55, y: 0.45, size: sq_size },
    { x: 0.4, y: -0.4, size: sq_size },
  ],
  3: [
    { x: -0.4, y: -0.5, size: sq_size },
    { x: -0.4, y: 0.4, size: sq_size },
    { x: 0.4, y: 0.4, size: sq_size },
    { x: 0.4, y: -0.4, size: sq_size },
  ],
  4: [
    { x: -0.4, y: -0.4, size: sq_size },
    { x: -0.4, y: 0.4, size: sq_size },
    { x: 0.4, y: 0.4, size: sq_size },
    { x: 0.4, y: -0.5, size: sq_size },
  ],
  5: [
    { x: -0.4, y: -0.5, size: sq_size },
    { x: -0.4, y: 0.4, size: sq_size },
    { x: 0.4, y: 0.4, size: sq_size },
    { x: 0.45, y: -0.55, size: sq_size },
  ],
  6: [
    { x: -0.4, y: -0.4, size: sq_size },
    { x: -0.4, y: 0.5, size: sq_size },
    { x: 0.4, y: 0.4, size: sq_size },
    { x: 0.5, y: -0.4, size: sq_size },
  ],
  7: [
    { x: -0.4, y: -0.4, size: sq_size },
    { x: -0.4, y: 0.6, size: sq_size },
    { x: 0.4, y: 0.4, size: sq_size },
    { x: 0.4, y: -0.4, size: sq_size },
  ],
  8: [
    { x: -0.4, y: -0.4, size: sq_size },
    { x: -0.4, y: 0.4, size: sq_size },
    { x: 0.5, y: 0.4, size: sq_size },
    { x: 0.7, y: -0.2, size: sq_size },
  ],
  9: [
    { x: -0.4, y: -0.4, size: sq_size },
    { x: -0.6, y: 0.4, size: sq_size },
    { x: 0.4, y: 0.4, size: sq_size },
    { x: 0.7, y: -0.2, size: sq_size },
  ],
  10: [
    { x: -0.3, y: -0.65, size: sq_size },
    { x: -0.4, y: 0.4, size: sq_size },
    { x: 0.6, y: 0.4, size: sq_size },
    { x: 0.4, y: -0.4, size: sq_size },
  ],
  11: [
    { x: -0.35, y: -0.65, size: sq_size },
    { x: -0.3, y: 0.65, size: sq_size },
    { x: 0.4, y: 0.4, size: sq_size },
    { x: 0.4, y: -0.4, size: sq_size },
  ],
  12: [
    { x: -0.4, y: -0.4, size: sq_size },
    { x: -0.5, y: 0.4, size: sq_size },
    { x: 0.4, y: 0.4, size: sq_size },
    { x: 0.4, y: -0.4, size: sq_size },
  ],
};

export const tokenSlotMap: Record<number, SquareProps[]> = {
  1: [
    { x: 0, y: -0.4, size: sq_size },
    { x: -0.6, y: 0.0, size: sq_size },
    { x: 0.0, y: 0.4, size: sq_size },
    { x: 0.4, y: 0, size: sq_size },
  ],
  2: [
    { x: 0, y: -0.55, size: sq_size },
    { x: -0.6, y: 0.0, size: sq_size },
    { x: 0.0, y: 0.7, size: sq_size },
    { x: 0.55, y: 0, size: sq_size },
  ],
  3: [
    { x: 0, y: -0.5, size: sq_size },
    { x: -0.6, y: 0.0, size: sq_size },
    { x: 0.0, y: 0.4, size: sq_size },
    { x: 0.4, y: 0, size: sq_size },
  ],
  4: [
    { x: 0, y: -0.4, size: sq_size },
    { x: -0.6, y: 0.0, size: sq_size },
    { x: 0.0, y: 0.4, size: sq_size },
    { x: 0.0, y: 0, size: sq_size },
  ],
  5: [
    { x: 0, y: -0.55, size: sq_size },
    { x: -0.7, y: 0.0, size: sq_size },
    { x: 0, y: 0.4, size: sq_size },
    { x: 0.65, y: 0, size: sq_size },
  ],
  6: [
    { x: 0, y: -0.7, size: sq_size },
    { x: -0.7, y: 0.0, size: sq_size },
    { x: 0.0, y: 0.5, size: sq_size },
    { x: 0.5, y: 0, size: sq_size },
  ],
  7: [
    { x: 0, y: -0.15, size: sq_size },
    { x: -0.7, y: 0.0, size: sq_size },
    { x: 0.0, y: 0.6, size: sq_size },
    { x: 0.4, y: 0, size: sq_size },
  ],
  8: [
    { x: -0.05, y: -0.5, size: sq_size },
    { x: -0.7, y: 0.0, size: sq_size },
    { x: 0.0, y: 0.55, size: sq_size },
    { x: -0.3, y: 0, size: sq_size },
  ],
  9: [
    { x: -0.05, y: -0.6, size: sq_size },
    { x: -0.6, y: 0.0, size: sq_size },
    { x: -0.1, y: 0.0, size: sq_size },
    { x: 0.3, y: 0, size: sq_size },
  ],
  10: [
    { x: 0.05, y: -0.4, size: sq_size },
    { x: -0.6, y: 0.05, size: sq_size },
    { x: 0.0, y: 0.1, size: sq_size },
    { x: 0.4, y: 0, size: sq_size },
  ],
  11: [
    { x: 0.05, y: -0.6, size: sq_size },
    { x: -0.7, y: 0.0, size: sq_size },
    { x: 0.05, y: 0.4, size: sq_size },
    { x: 0.6, y: 0, size: sq_size },
  ],
  12: [
    { x: 0, y: -0.4, size: sq_size },
    { x: -0.7, y: 0.0, size: sq_size },
    { x: -0.3, y: 0.0, size: sq_size },
    { x: 0.05, y: 0, size: sq_size },
  ],
};