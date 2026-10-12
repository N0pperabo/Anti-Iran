# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

added_files = [
    ('schemas', 'schemas'),
    ('workflows', 'workflows'),
    ('.github', '.github'),
]

hidden_imports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'cryptography.fernet',
    'keyring',
    'keyring.backends',
    'keyring.backends.Windows',
    'httpx',
    'pydantic',
    'automation.runner',
    'automation.browser',
    'automation.actions',
    'automation.selectors',
    'automation.state',
    'automation.inspector',
    'automation.reporting',
    'models.action_types',
    'models.workflow',
    'models.inspect_bundle',
    'models.run_report',
    'github.client',
    'github.models',
    'github.poller',
    'github.exceptions',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BrowserAutomationStudio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BrowserAutomationStudio',
)
