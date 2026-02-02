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
             datas=[('src/blescanner.kv', '.'),
                    ('src/characteristicframekivy.kv', '.'),
                    ('src/collapsibleframekivy.kv', '.'),
                    ('src/descriptorframekivy.kv', '.'),
                    ('src/deviceframekivy.kv', '.')],
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
