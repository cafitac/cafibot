import { getWrappedLineCount } from './TextInput.js';

export const DEFAULT_TERMINAL_COLUMNS = 80;

export type SmartInputMode = 'autocomplete' | 'cursor' | 'history';

export function getTerminalColumns(columns?: number): number {
  const resolvedColumns = columns ?? process.stdout.columns;
  return typeof resolvedColumns === 'number' && Number.isFinite(resolvedColumns) && resolvedColumns > 0
    ? resolvedColumns
    : DEFAULT_TERMINAL_COLUMNS;
}

export function getInputWrapWidth(columns?: number): number {
  return Math.max(10, getTerminalColumns(columns) - 6);
}

export function getDialogWidth(columns?: number): number {
  return Math.max(20, Math.min(getTerminalColumns(columns) - 4, 60));
}

export function getDisplayVersion(version?: string): string {
  const normalized = version?.trim();
  return normalized ? normalized : '?';
}

export function getSmartInputMode({
  value,
  showAutocomplete,
  columns,
}: {
  value: string;
  showAutocomplete: boolean;
  columns?: number;
}): SmartInputMode {
  if (showAutocomplete) {
    return 'autocomplete';
  }

  const wrapWidth = getInputWrapWidth(columns);
  if (value.includes('\n') || getWrappedLineCount(value, wrapWidth) > 1) {
    return 'cursor';
  }

  return 'history';
}
