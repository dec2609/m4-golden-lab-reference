/** A view may only commit the latest request, including its error/loading state. */
export function createRequestScope() {
  let active: AbortController | undefined;
  return {
    start() {
      active?.abort();
      const controller = new AbortController();
      active = controller;
      return {
        signal: controller.signal,
        isCurrent: () => active === controller && !controller.signal.aborted,
      };
    },
    cancel() { active?.abort(); active = undefined; },
  };
}
