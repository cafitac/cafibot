import { getWrappedLineCount } from './TextInput.js';
export const DEFAULT_TERMINAL_COLUMNS = 80;
export function getTerminalColumns(columns) {
    const resolvedColumns = columns ?? process.stdout.columns;
    return typeof resolvedColumns === 'number' && Number.isFinite(resolvedColumns) && resolvedColumns > 0
        ? resolvedColumns
        : DEFAULT_TERMINAL_COLUMNS;
}
export function getInputWrapWidth(columns) {
    return Math.max(10, getTerminalColumns(columns) - 6);
}
export function getDialogWidth(columns) {
    return Math.max(20, Math.min(getTerminalColumns(columns) - 4, 60));
}
export function getDisplayVersion(version) {
    const normalized = version?.trim();
    return normalized ? normalized : '?';
}
export function getSmartInputMode({ value, showAutocomplete, columns, }) {
    if (showAutocomplete) {
        return 'autocomplete';
    }
    const wrapWidth = getInputWrapWidth(columns);
    if (value.includes('\n') || getWrappedLineCount(value, wrapWidth) > 1) {
        return 'cursor';
    }
    return 'history';
}
