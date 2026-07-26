import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Link to a file on GitHub (default branch). */
export function ghBlobUrl(fullName: string, branch: string, path: string): string {
  return `https://github.com/${fullName}/blob/${branch}/${path
    .split("/")
    .map(encodeURIComponent)
    .join("/")}`;
}

/** Link to a directory (module) on GitHub, or the repo root for "(root)". */
export function ghTreeUrl(fullName: string, branch: string, module: string): string {
  if (!module || module === "(root)") {
    return `https://github.com/${fullName}/tree/${branch}`;
  }
  return `https://github.com/${fullName}/tree/${branch}/${module
    .split("/")
    .map(encodeURIComponent)
    .join("/")}`;
}
