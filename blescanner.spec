# -*- mode: python ; coding: utf-8 -*-
import sys
from kivy.tools.packaging.pyinstaller_hooks import hookspath as kivy_hookspath, runtime_hooks as kivy_runtime_hooks

block_cipher = None

# Platform-specific dependencies for Kivy on Windows. On Linux and macOS,
# the Kivy PyInstaller hooks will automatically pick up the required system
# libraries (e.g., SDL2, GLEW) if they are installed.
kivy_deps_trees = []
if sys.platform == 'win32':
    from kivy_deps import sdl2, glew
    kivy_deps_trees = [Tree(p) for p in (sdl2.dep_bins + glew.dep_bins)]


a = Analysis(['src/main.py'],
             pathex=['.'],
             binaries=[],
             datas=[('src/blescanner/assets', 'blescanner/assets'),
                    ('src/blescanner/ui/main.kv', 'blescanner/ui'),
                    ('src/blescanner/ui/settings_popup.kv', 'blescanner/ui'),
                    ('src/blescanner/tools/noise_monitor/noise_monitor_settings.kv', 'blescanner/tools/noise_monitor'),
                    ('src/blescanner/tools/serial_monitor/serial_monitor_settings.kv', 'blescanner/tools/serial_monitor'),
                    ('src/blescanner/tools/ble_scanner/*.kv', 'blescanner/tools/ble_scanner'),
                    ('src/blescanner/tools/serial_monitor/serial_monitor.kv', 'blescanner/tools/serial_monitor'),
                    ('src/blescanner/tools/audio_analyzer/audio_analyzer.kv', 'blescanner/tools/audio_analyzer'),
                    ('src/blescanner/tools/calculator/calculator.kv', 'blescanner/tools/calculator'),
                    ('src/blescanner/tools/hex_editor/hex_editor.kv', 'blescanner/tools/hex_editor'),
                    ('src/blescanner/tools/joystick_tester/joystick_tester.kv', 'blescanner/tools/joystick_tester'),
                    ('src/blescanner/tools/network_scanner/network_scanner.kv', 'blescanner/tools/network_scanner'),
                    ('src/blescanner/tools/noise_monitor/noise_monitor.kv', 'blescanner/tools/noise_monitor'),
                    ('src/blescanner/tools/sys_info/sys_info.kv', 'blescanner/tools/sys_info'),
                    ('src/blescanner/tools/terminal/terminal.kv', 'blescanner/tools/terminal'),
                    ('src/blescanner/tools/wifi_scanner/wifi_scanner.kv', 'blescanner/tools/wifi_scanner'),
                    ('src/blescanner/tools/ftp_server/*.kv', 'blescanner/tools/ftp_server')],
             hiddenimports=[
                 'kivy.core.image.img_sdl2',
                 'kivy.core.text.text_sdl2',
                 'kivy.core.window.window_sdl2'
             ],
             hookspath=kivy_hookspath(),
             runtime_hooks=kivy_runtime_hooks(),
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='blescanner',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               *kivy_deps_trees,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='BLEScanner')
