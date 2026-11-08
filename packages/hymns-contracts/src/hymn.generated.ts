/* Generated from schemas/hymn.schema.json. Run pnpm --filter @hinario/hymns-contracts generate. */

/**
 * This interface was referenced by `Hymn`'s JSON-Schema
 * via the `definition` "SectionType".
 */
export type SectionType = "verse" | "chorus";

export interface Hymn {
  id: string;
  number: number;
  title: string;
  sections: HymnSection[];
  version: number;
  updatedAt?: string;
  deleted?: boolean;
}
/**
 * This interface was referenced by `Hymn`'s JSON-Schema
 * via the `definition` "HymnSection".
 */
export interface HymnSection {
  type: SectionType;
  number?: number;
  /**
   * @minItems 1
   */
  lines: string[];
}
/**
 * This interface was referenced by `Hymn`'s JSON-Schema
 * via the `definition` "HinarioMetadata".
 */
export interface HinarioMetadata {
  currentVersion: number;
  updatedAt: string;
  totalHymns?: number;
  releaseHash?: string;
}
