import nextPlugin from "@next/eslint-plugin-next";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

const eslintConfig = tseslint.config(
  {
    ignores: [".next/**", "node_modules/**", "out/**", "build/**"],
  },
  {
    files: ["**/*.{js,jsx,ts,tsx}"],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
    },
    ...nextPlugin.configs["core-web-vitals"],
    ...reactHooks.configs.flat.recommended,
    rules: {
      // 这两个模式（SSR mount 标记、prop 同步到本地 state）是故意的；
      // react-hooks v7 的新规则过严，关闭之。
      "react-hooks/set-state-in-effect": "off",
    },
  },
);

export default eslintConfig;
