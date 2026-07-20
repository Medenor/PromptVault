/**
 * Debounce a function, delaying invocation until `wait` ms have passed
 * since the last call.
 */
export function debounce<T extends (...args: never[]) => void>(fn: T, wait: number): T {
  let timeout: ReturnType<typeof setTimeout> | null = null;

  return function debounced(this: unknown, ...args: Parameters<T>): void {
    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(() => {
      timeout = null;
      fn.apply(this, args);
    }, wait);
  } as T;
}
