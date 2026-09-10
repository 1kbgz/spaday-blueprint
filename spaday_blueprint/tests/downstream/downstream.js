/* A stand-in for a downstream component library built on Blueprint.
 *
 * It imports Blueprint the way a library built on it does, by Blueprint's own bare specifiers, left
 * as imports in its bundle. spaday-blueprint publishes its copy under those specifiers in the page's
 * import map, so they resolve to the modules that already registered the catalog: the page keeps
 * one copy, and nothing registers the same tag names twice.
 */

import { BpButton } from "@blueprintui/components/button";
import "@blueprintui/components/include/button.js";

class DemoAction extends HTMLElement {
  connectedCallback() {
    if (this.firstElementChild) return;
    // constructed from the imported class, which throws unless it is the registered one
    const button = new BpButton();
    button.textContent = this.getAttribute("label") ?? "Go";
    this.append(button);
  }
}

if (!customElements.get("demo-action")) {
  customElements.define("demo-action", DemoAction);
}
