# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['main.py'],
             pathex=[
               r'C:\Users\synthbot\animate-tools\auto-adobeanimate',
             ],
             binaries=[],
             datas=[
                ("animate-scripts-dist/*.jsfl", "./animate-scripts-dist"),
                ("animate-tests/*.fla", "./animate-tests"),
                ("../xflsvg/xflsvg/xfl_template", "./xflsvg/xfl_template")
             ],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='main',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='auto-animate')
