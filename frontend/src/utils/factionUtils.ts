import type { components } from "../api/types";

export type FactionCode =
  components["schemas"]["PlayerPublic"]["faction"]["value"];
export type FactionLabel =
  components["schemas"]["PlayerPublic"]["faction"]["label"];

/**
 * Converts a faction label to a kebab-case route name.
 * e.g., "Woodland Alliance" -> "woodland-alliance"
 */
export const labelToRoute = (label: FactionLabel): string => {
  return label.toLowerCase().replace(/\s+/g, "-");
};

/**
 * Type-level helper to derive the kebab-case faction names from labels.
 * This matches the logic in labelToRoute but at the type level.
 */
export type KebabCase<S extends string> = S extends `${infer T} ${infer U}`
  ? `${Lowercase<T>}-${KebabCase<U>}`
  : Lowercase<S>;

export type FactionValue = KebabCase<FactionLabel>;
