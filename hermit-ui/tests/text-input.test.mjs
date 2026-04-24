import test from 'node:test';
import assert from 'node:assert/strict';

import {
  getCursorPositionForWrappedText,
  getWrappedLineCount,
} from '../dist/TextInput.js';

test('getWrappedLineCount counts soft-wrapped visual lines', () => {
  assert.equal(getWrappedLineCount('abcd', 3), 2);
  assert.equal(getWrappedLineCount('ab\ncd', 10), 2);
});

test('getCursorPositionForWrappedText respects wide graphemes', () => {
  assert.deepEqual(getCursorPositionForWrappedText('가a', 2), { line: 1, column: 1 });
  assert.deepEqual(getCursorPositionForWrappedText('🙂a', 2), { line: 1, column: 1 });
});
