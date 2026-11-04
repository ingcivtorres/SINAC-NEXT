import js from '@eslint/js';
import globals from 'globals';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';

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
    plugins: {react, 'react-hooks': reactHooks},
    rules: {
      ...js.configs.recommended.rules,
      'no-unused-vars': ['error', {args: 'none', caughtErrors: 'none', ignoreRestSiblings: true}],
      'no-empty': ['error', {allowEmptyCatch: true}],
      'react/jsx-uses-react': 'error',
      'react/jsx-uses-vars': 'error',
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
    },
  },
];
