import test from 'node:test';
import assert from 'node:assert/strict';

import {
  DEFAULT_TERMINAL_COLUMNS,
  getDialogWidth,
  getDisplayVersion,
  getInputWrapWidth,
  getMainInputWrapWidth,
  getSmartInputMode,
  getTerminalColumns,
  MAIN_INPUT_PROMPT,
} from '../dist/uiModel.js';
import { getInitialStatusHints } from '../dist/startupStatus.js';

test('getDisplayVersion normalizes empty versions to a placeholder', () => {
  assert.equal(getDisplayVersion(undefined), '?');
  assert.equal(getDisplayVersion(''), '?');
  assert.equal(getDisplayVersion(' 0.3.9 '), '0.3.9');
});

test('terminal sizing helpers keep reasonable defaults', () => {
  assert.equal(getTerminalColumns(undefined), DEFAULT_TERMINAL_COLUMNS);
  assert.equal(getInputWrapWidth(20), 14);
  assert.equal(getMainInputWrapWidth(20), 16);
  assert.equal(MAIN_INPUT_PROMPT, '❯ ');
  assert.equal(getDialogWidth(200), 60);
  assert.equal(getDialogWidth(12), 20);
});

test('smart input mode prefers autocomplete, then cursor, then history', () => {
  assert.equal(
    getSmartInputMode({ value: '/he', showAutocomplete: true, columns: 80 }),
    'autocomplete',
  );
  assert.equal(
    getSmartInputMode({ value: '01234567890', showAutocomplete: false, columns: 12 }),
    'cursor',
  );
  assert.equal(
    getSmartInputMode({ value: 'single line', showAutocomplete: false, columns: 80 }),
    'history',
  );
});

test('getInitialStatusHints prefers explicit env and local settings over global settings', () => {
  const files = new Map([
    ['/home/test/.hermit/settings.json', JSON.stringify({ model: 'global-model' })],
    ['/repo/.hermit/settings.json', JSON.stringify({ model: 'local-model' })],
  ]);
  const fsImpl = {
    readFileSync(filePath) {
      const value = files.get(String(filePath));
      if (!value) {
        throw new Error('missing');
      }
      return value;
    },
  };

  assert.deepEqual(
    getInitialStatusHints({
      env: { HERMIT_UI_VERSION: '0.3.9' },
      cwd: '/repo',
      homeDir: '/home/test',
      fsImpl,
    }),
    { version: '0.3.9', model: 'local-model' },
  );

  assert.deepEqual(
    getInitialStatusHints({
      env: { HERMIT_UI_VERSION: '0.3.9', HERMIT_MODEL: 'env-model' },
      cwd: '/repo',
      homeDir: '/home/test',
      fsImpl,
    }),
    { version: '0.3.9', model: 'env-model' },
  );
});
