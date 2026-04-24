import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

type SettingsShape = {
  model?: string;
};

export type StartupStatusHints = {
  version?: string;
  model?: string;
};

function readSettingsFile(settingsPath: string, fsImpl: Pick<typeof fs, 'readFileSync'>): SettingsShape {
  try {
    const raw = fsImpl.readFileSync(settingsPath, 'utf8');
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed as SettingsShape : {};
  } catch {
    return {};
  }
}

function normalizeModel(model: string | undefined): string | undefined {
  const trimmed = model?.trim();
  return trimmed && trimmed !== '__auto__' ? trimmed : undefined;
}

export function getInitialStatusHints({
  env = process.env,
  cwd = process.cwd(),
  homeDir = os.homedir(),
  fsImpl = fs,
}: {
  env?: NodeJS.ProcessEnv;
  cwd?: string;
  homeDir?: string;
  fsImpl?: Pick<typeof fs, 'readFileSync'>;
} = {}): StartupStatusHints {
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
