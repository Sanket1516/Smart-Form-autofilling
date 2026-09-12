import js from "@eslint/js";
import globals from "globals";
import { defineConfig } from "eslint/config";

export default defineConfig([
  { ignores: ["**/node_modules/**", "frontend/dist/**"] },
  {
    files: ["frontend/src/**/*.js", "frontend/src/**/*.jsx"],
    ...js.configs.recommended,
    languageOptions: {
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: { "no-unused-vars": "off" },
  },
  {
    files: ["extension/**/*.js"],
    ...js.configs.recommended,
    languageOptions: { globals: { ...globals.browser, chrome: "readonly" } },
  },
]);

