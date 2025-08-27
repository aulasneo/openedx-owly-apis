// Commitlint configuration for Conventional Commits
// Docs: https://github.com/conventional-changelog/commitlint

/** @type {import('@commitlint/types').UserConfig} */
export default {
  // Use the standard conventional commit rules
  extends: ['@commitlint/config-conventional'],
  // Optionally tailor a few rules to be less strict on casing
  rules: {
    // Allow any casing in subject (prevents common false negatives)
    'subject-case': [2, 'never', ['sentence-case', 'start-case', 'pascal-case', 'upper-case']],
    // Enforce a reasonable header length
    'header-max-length': [2, 'always', 100],
    // Typical allowed types
    'type-enum': [
      2,
      'always',
      [
        'build',
        'chore',
        'ci',
        'docs',
        'feat',
        'fix',
        'perf',
        'refactor',
        'revert',
        'style',
        'test'
      ]
    ]
  }
};
