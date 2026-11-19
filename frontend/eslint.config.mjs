import js from '@eslint/js';
import globals from 'globals';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import jsxA11y from 'eslint-plugin-jsx-a11y';

export default [
  {ignores: ['build/**', 'node_modules/**']},
  {
    files: ['src/**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: globals.browser,
      parserOptions: {ecmaFeatures: {jsx: true}},
    },
    settings: {react: {version: 'detect'}},
    plugins: {react, 'react-hooks': reactHooks, 'jsx-a11y': jsxA11y},
    rules: {
      ...js.configs.recommended.rules,
      ...jsxA11y.flatConfigs.recommended.rules,
      // autoFocus solo se usa en diálogos y formularios que el usuario acaba de abrir.
      'jsx-a11y/no-autofocus': 'off',
      'jsx-a11y/label-has-associated-control': ['error', {assert: 'either', depth: 4}],
      'no-unused-vars': ['error', {args: 'none', caughtErrors: 'none', ignoreRestSiblings: true}],
      'no-empty': ['error', {allowEmptyCatch: true}],
      'react/jsx-uses-react': 'error',
      'react/jsx-uses-vars': 'error',
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
    },
  },
];
