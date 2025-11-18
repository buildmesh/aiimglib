export function resetReferenceSearchState(state, query) {
  if (!state) {
    throw new Error("state is required");
  }
  const nextQuery = typeof query === "string" ? query.trim() : "";
  state.currentQuery = nextQuery;
  state.page = 1;
  return state;
}
