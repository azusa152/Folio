/**
 * Type-safe bridge between openapi-fetch responses and local view-model types.
 *
 * After `if (error) throw error`, the openapi-fetch client guarantees `data` is
 * defined for 2xx responses. TypeScript cannot infer this narrowing, so we
 * centralise it here rather than scattering `as unknown as T` across every hook.
 *
 * For schema-derived types (components["schemas"]["..."]) this is always safe —
 * the generated paths type matches the local alias exactly.
 *
 * For hand-written types (e.g. EnrichedStock, FxAnalysisState) the caller must
 * verify the backend shape matches the local interface at the call-site.
 */
export function fromApiData<T>(data: unknown): T {
  if (data == null) {
    throw new Error("fromApiData: expected defined response data after error guard")
  }
  return data as T
}
