// the guard must execute before the upstream imports register their elements
import { restoreDefine } from "./define-guard.js";
import "@blueprintui/components/include/all.js";

restoreDefine(`@blueprintui/components ${__BLUEPRINT_VERSION__}`);

declare const __BLUEPRINT_VERSION__: string;

// the version actually served, so a page holding a second copy can compare and refuse rather than
// half-work
Object.defineProperty(globalThis, "__spadayBlueprint", {
  value: Object.freeze({ version: __BLUEPRINT_VERSION__ }),
  configurable: true,
  enumerable: false,
  writable: false,
});
