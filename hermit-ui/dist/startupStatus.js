import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
function readSettingsFile(settingsPath, fsImpl) {
    try {
        const raw = fsImpl.readFileSync(settingsPath, 'utf8');
        const parsed = JSON.parse(raw);
        return parsed && typeof parsed === 'object' ? parsed : {};
    }
    catch {
        return {};
    }
}
function normalizeModel(model) {
    const trimmed = model?.trim();
    return trimmed && trimmed !== '__auto__' ? trimmed : undefined;
}
export function getInitialStatusHints({ env = process.env, cwd = process.cwd(), homeDir = os.homedir(), fsImpl = fs, } = {}) {
    const version = env.HERMIT_UI_VERSION?.trim() || undefined;
    const explicitModel = normalizeModel(env.HERMIT_UI_MODEL) || normalizeModel(env.HERMIT_MODEL);
    if (explicitModel) {
        return { version, model: explicitModel };
    }
    const globalSettings = readSettingsFile(path.join(homeDir, '.hermit', 'settings.json'), fsImpl);
    const localSettings = readSettingsFile(path.join(cwd, '.hermit', 'settings.json'), fsImpl);
    const model = normalizeModel(localSettings.model) || normalizeModel(globalSettings.model);
    return { version, model };
}
