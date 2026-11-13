import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import pluginVue from 'eslint-plugin-vue'

export default defineConfigWithVueTs(
  { name: 'app/files-to-lint', files: ['**/*.{ts,mts,vue}'] },
  { name: 'app/files-to-ignore', ignores: ['**/dist/**', '**/coverage/**', 'src/api/schema.d.ts'] },
  pluginVue.configs['flat/recommended'],
  vueTsConfigs.recommendedTypeChecked,
  {
    name: 'app/rules',
    rules: {
      // Optional TypeScript props are `undefined` by default: no runtime default needed.
      'vue/require-default-prop': 'off',
    },
  },
  {
    name: 'app/tests',
    files: ['tests/**/*.ts'],
    rules: {
      // `vi.mocked(api.get)` references methods on purpose to configure mocks.
      '@typescript-eslint/unbound-method': 'off',
    },
  },
  skipFormatting,
)
