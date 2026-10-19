import tseslint from 'typescript-eslint';

export default tseslint.config(
  ...tseslint.configs.recommended,
  {files: ['**/*.mjs'], languageOptions: {globals: {process: 'readonly', console: 'readonly', URL: 'readonly'}}},
);
