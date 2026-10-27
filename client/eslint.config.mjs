import nextVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

const config = [...nextVitals, ...nextTypescript, {
  // shortcut: retain the React18 hook policy; revisit these diagnostics when adopting React Compiler.
  rules: {
    "react-hooks/set-state-in-effect": "off",
    "react-hooks/preserve-manual-memoization": "off",
  },
}];
export default config;
